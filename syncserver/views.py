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


@view_config(route_name='get_record', renderer='json')
def get_record_view(request):
    '''
    GET /{name}/{section}/{id}/record
        < {}
        > {'record': json}
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


@view_config(route_name='put_record', renderer='json')
def put_record_view(request):
    '''
    PUT /{name}/{section}/{id}/record
        < {'lock_key': uuid, 'record': json}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    record = request.json_body.get('record')
    if record is None:
        raise HTTPBadRequest("No record specified")

    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.insert_or_update_record(config, section_name, record_id, record)
    return {}


@view_config(route_name='delete_record', renderer='json')
def delete_record_view(request):
    '''
    DELETE /{name}/{section}/{id}/record
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_record(config, section_name, record_id)
    return {}


@view_config(route_name='get_hash', renderer='json')
def get_hash_view(request):
    '''
    GET /{name}/{section}/{id}/hash
        < {}
        > {'hash': hash}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    hash = record_database.get_record_hash(config, section, record_id)
    if hash is None:
        raise NotFound
    return {'hash': hash}


@view_config(route_name='put_hash', renderer='json')
def put_hash_view(request):
    '''
    PUT /{name}/{section}/{id}/hash
        < {'lock_key': uuid, 'hash': uuid}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    hash = request.json_body.get('hash')
    if hash is None:
        raise HTTPBadRequest("No hash specified")

    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.insert_or_update_hash(config, section_name, record_id, hash)
    return {}


@view_config(route_name='delete_hash', renderer='json')
def delete_hash_view(request):
    '''
    DELETE /{name}/{section}/{id}/hash
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_hash(config, section_name, record_id)
    return {}


@view_config(route_name='get_record_and_hash', renderer='json')
def get_record_and_hash_view(request):
    '''
    GET /{name}/{section}/{id}/record-hash
        < {}
        > {'record': json, 'hash': uuid}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    record = record_database.get_record(config, section, record_id)
    hash = record_database.get_record_hash(config, section, record_id)
    if (record is None) or (hash is None):
        raise NotFound
    return {'record': record, 'hash': hash}


@view_config(route_name='put_record_and_hash', renderer='json')
def put_record_and_hash_view(request):
    '''
    PUT /{name}/{section}/{id}/record-hash
        < {'lock_key': uuid, 'record': json, 'hash': uuid}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    record = request.json_body.get('record')
    hash = request.json_body.get('hash')
    if record is None:
        raise HTTPBadRequest("No record specified")

    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.insert_or_update_record(config, section_name, record_id, record)
    record_database.insert_or_update_hash(config, section_name, record_id, hash)
    return {}


@view_config(route_name='delete_record_and_hash', renderer='json')
def delete_record_and_hash_view(request):
    '''
    DELETE /{name}/{section}/{id}/record-hash
        < {'lock_key': uuid}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = request.matchdict['id']
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_record(config, section_name, record_id)
    record_database.delete_hash(config, section_name, record_id)
    return {}
