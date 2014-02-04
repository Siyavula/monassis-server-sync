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
    Lock,
    LockError,
)

from syncserver.errors import DatabaseLocked
from syncserver.requests import log_request
from syncserver import utils
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


@view_config(route_name='get_hash_hash', renderer='json')
def get_hash_hash_view(request):
    '''
    GET /{name}/hash-hash
        < {}
        > {'hash-hash': hash}
    '''
    sync_name = request.matchdict['name']
    config = record_database.load_config_from_name(sync_name, 'server')
    return {'hash-hash': record_database.get_hash_hash(config)}


@view_config(route_name='get_hash_actions', renderer='json')
def get_hash_actions_view(request):
    '''
    GET /{name}/hash-actions
        < {'lock_key': uuid, 'sync_time': iso8601, 'client_vars': {name: value}}
        > {'hash_actions': {section: {id: ('insert', hash) / ('update', hash) / ('delete',)}}}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    sync_time = utils.parse_iso8601(request.json_body['sync_time'])
    client_vars = dict([(k, utils.json_to_struct(v)) for k, v in request.json_body['client_vars'].iteritems()])
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    config = record_database.load_config_from_name(sync_name, 'server', run_setup=True, sync_time=sync_time, client_vars=client_vars)
    hash_actions = record_database.get_hash_actions(config)
    return {'hash_actions': utils.actions_to_json(hash_actions)}


@view_config(route_name='get_hash_actions_for_section', renderer='json')
def get_hash_actions_for_section_view(request):
    '''
    GET /{name}/hash-actions/{section}
        < {'lock_key': uuid, 'sync_time': iso8601, 'client_vars': {name: value}}
        > {'hash_actions': {section: {id: ('insert', hash) / ('update', hash) / ('delete',)}}}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    sync_time = utils.parse_iso8601(request.json_body['sync_time'])
    client_vars = dict([(k, utils.json_to_struct(v)) for k, v in request.json_body['client_vars'].iteritems()])
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section = request.matchdict['section']
    config = record_database.load_config_from_name(sync_name, 'server', run_setup=True, sync_time=sync_time, client_vars=client_vars)
    hash_actions = record_database.get_hash_actions(config, section=section)
    return {'hash_actions': utils.actions_to_json(hash_actions)}


@view_config(route_name='get_record', renderer='json')
def get_record_view(request):
    '''
    GET /{name}/records/{section}/{id}
        < {}
        > {'record': {key: value}}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    record = record_database.get_record(config, section, record_id)
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
