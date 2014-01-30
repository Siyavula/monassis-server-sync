from pyramid.response import Response
from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import view_config

from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm.attributes import instance_dict

import logging
log = logging.getLogger(__name__)

from .models import (
    DBSession,
    RecordHash,
    Lock,
    LockError,
)

from syncserver.errors import DatabaseLocked
from syncserver.requests import log_request
from syncserver.utils import parse_iso8601
import syncserver.record_database as record_database

@view_config(route_name='lock', renderer='json')
def lock_view(request):
    '''
    PUT /{name}/lock
        < {}
        > {'lock_key': uuid}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    try:
        key = Lock.obtain_lock(sync_name)
    except LockError:
        raise DatabaseLocked("The database is already locked by someone else")
    return {'lock_key': key}


@view_config(route_name='unlock', renderer='json')
def unlock_view(request):
    '''
    PUT /{name}/unlock
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    try:
        Lock.release_lock(sync_name, key)
    except LockError:
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    return {}


def __get_all_hashes_for(sync_name):
    hash_hierarchy = {}
    for h in RecordHash.get_all_for(sync_name):
        section = hash_hierarchy.set_default(h['section'], {})
        section[h['key']] = h['hash']
    return hash_hierarchy


@view_config(route_name='get_hashes', renderer='json')
def get_hashes_view(request):
    '''
    GET /{name}/hashes
        < {}
        > {'hashes': {section_name: {ident: hash}}}
    '''
    sync_name = request.matchdict['name']
    hash_hierarchy = __get_all_hashes_for(sync_name)
    return {'hashes': hash_hierarchy}


@view_config(route_name='get_hash_actions', renderer='json')
def get_hash_actions_view(request):
    '''
    GET /{name}/hash-actions
        < {'lock_key': uuid}
        > {'hash_actions': {section_name: {'insert': {ident: hash}, 'update': {ident: hash}, 'delete': [ident]}}}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    old_hash_hierarchy = __get_all_hashes_for(sync_name)
    new_hash_hierarchy = record_database.get_all_hashes_for(sync_name)
    hash_actions = compute_hash_actions(old_hash_hierarchy, new_hash_hierarchy)
    return {'hash_actions': hash_actions}


@view_config(route_name='get_record', renderer='json')
def get_record_view(request):
    '''
    GET /{name}/records/{section}/{id}
        < {}
        > {'record': {key: value}}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section = request.matchdict['key']
    record_id = request.matchdict['id']
    record = record_database.get_record(sync_name, section, record_id)
    if record is None:
        raise NotFound
    return {'record': record}


@view_config(route_name='delete_hash', renderer='json')
def delete_hash_view(request):
    '''
    DELETE /{name}/hashes/{section}/{id}
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section = request.matchdict['key']
    record_id = request.matchdict['id']
    RecordHash.delete(sync_name, section, record_id)
    return {}


@view_config(route_name='put_record', renderer='json')
def put_record_view(request):
    '''
    PUT /{name}/records/{section}/{id}
        < {'lock_key': uuid, 'record': {key: value}}
        > {'hash': string}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section = request.matchdict['key']
    record_id = request.matchdict['id']
    record = request.json_body.get('record')
    if record is None:
        raise HTTPBadRequest("No record specified")

    new_hash = record_database.insert_or_update_record(sync_name, section, record_id, record)
    record_hash = RecordHash.get(sync_name, section, record_id)
    if record_hash is None:
        record_hash = RecordHash.create(sync_name, section, record_id, new_hash)
    else:
        record_hash.update(new_hash)
    return {'hash': new_hash}


@view_config(route_name='delete_record', renderer='json')
def delete_record_view(request):
    '''
    DELETE /{name}/records/{section}/{id}
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section = request.matchdict['key']
    record_id = request.matchdict['id']
    record_database.delete_record(sync_name, section, record_id)
    RecordHash.delete(sync_name, section, record_id)
    return {}
