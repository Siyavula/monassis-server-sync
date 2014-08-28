from pyramid.exceptions import NotFound
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import view_config

import logging
log = logging.getLogger(__name__)

from .models import (
    Lock,
    LockError,
)

from syncserver.errors import DatabaseLocked
from syncserver import utils
import syncserver.record_database as record_database


@view_config(route_name='lock', renderer='json')
def lock_view(request):
    '''
    PUT /{name}/lock
        < {}
        > {'lock_key': string}
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
        < {'lock_key': string}
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
        > {'hash-hash': user-defined-hash-hash}
    '''
    sync_name = request.matchdict['name']
    config = record_database.load_config_from_name(sync_name, 'server')
    return {'hash-hash': record_database.get_hash_hash(config)}


@view_config(route_name='get_hash_actions', renderer='json')
def get_hash_actions_view(request):
    '''
    GET /{name}/hash-actions
        < {'lock_key': string, 'sync_time': iso8601 (optional), 'client_vars': user-defined-client-vars (optional)}
        > {'hash_actions': {section_name (string): [[user-defined-record-id, ['insert', user-defined-hash] or ['update', user-defined-hash, user-defined-hash] or ['delete', user-defined-hash]]]}}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    sync_time = request.json_body.get('sync_time')
    try:
        sync_time = utils.parse_iso8601(sync_time)
    except ValueError:
        raise HTTPBadRequest("Bad sync_time format")
    client_vars = request.json_body.get('client_vars')

    print 'Sync time:', repr(sync_time)
    config = record_database.load_config_from_name(sync_name, 'server', run_setup=True, sync_time=sync_time, client_vars=client_vars)
    hash_actions = record_database.get_hash_actions(config)
    return {'hash_actions': hash_actions}


@view_config(route_name='get_record', renderer='json')
def get_record_view(request):
    '''
    GET /{name}/{section}/{id}/record
        < {}
        > {'record': user-defined-record}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    record = record_database.get_record(config, section_name, record_id)
    if record is None:
        raise NotFound
    return {'record': record}


@view_config(route_name='get_records_for_section', renderer='json')
def get_records_for_section_view(request):
    '''
    GET /{name}/{section}/records
        < {'record_ids': [user-defined-record-id, ...]}
        > {'records': [user-defined-record, ...]}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section_name = request.matchdict['section']
    record_ids = [record_database.url_string_to_record_id(x) for x in request.json_body.get('record_ids', [])]
    config = record_database.load_config_from_name(sync_name, 'server')
    records = [record_database.get_record(config, section_name, record_id) for record_id in record_ids]
    if None in records:
        raise NotFound
    return {'records': records}


@view_config(route_name='put_record', renderer='json')
def put_record_view(request):
    '''
    PUT /{name}/{section}/{id}/record
        < {'lock_key': string, 'record': user-defined-record}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
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
        < {'lock_key': string}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_record(config, section_name, record_id)
    return {}


@view_config(route_name='put_records_for_section', renderer='json')
def put_records_for_section_view(request):
    '''
    PUT /{name}/{section}/records
        < {
              'lock_key': string,
              'actions': [{
                  'action': ('put', 'delete'),
                  'id': user-defined-record-id,
                  'record': user-defined-record,
              }],
          }
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    actions = request.json_body.get('actions')
    if actions is None:
        raise HTTPBadRequest("No actions specified")

    for entry in actions:
        action = entry.get('action')
        if action is None:
            raise HTTPBadRequest("No action specified in %s" % repr(entry))
        elif action not in ['put', 'delete']:
            raise HTTPBadRequest("Unknown action %s" % repr(action))
        record_id = entry.get('id')
        if record_id is None:
            raise HTTPBadRequest("No record id specified in %s" % repr(entry))
        entry['id'] = record_database.url_string_to_record_id(record_id)
        if action == 'put':
            if entry.get('record') is None:
                raise HTTPBadRequest("No record specified in %s" % repr(entry))
        else:
            if entry.get('record') is not None:
                raise HTTPBadRequest("Unexpected record for delete action in %s" % repr(entry))

    config = record_database.load_config_from_name(sync_name, 'server')
    for entry in actions:
        action = entry['action']
        record_id = entry['id']
        if action == 'put':
            record = entry['record']
            record_database.insert_or_update_record(config, section_name, record_id, record)
        elif action == 'delete':
            record_database.delete_record(config, section_name, record_id)
        else:
            assert False
    return {}


@view_config(route_name='get_hash', renderer='json')
def get_hash_view(request):
    '''
    GET /{name}/{section}/{id}/hash
        < {}
        > {'hash': user-defined-hash}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    hash = record_database.get_hash(config, section_name, record_id)
    if hash is None:
        raise NotFound
    return {'hash': hash}


@view_config(route_name='put_hash', renderer='json')
def put_hash_view(request):
    '''
    PUT /{name}/{section}/{id}/hash
        < {'lock_key': string, 'hash': user-defined-hash}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    hash = request.json_body.get('hash')
    if hash is None:
        raise HTTPBadRequest("No hash specified")

    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.insert_or_update_hash(config, section_name, record_id, hash)
    return {}


@view_config(route_name='put_hashes_for_section', renderer='json')
def put_hashes_for_section_view(request):
    '''
    PUT /{name}/{section}/hashes
        < {
              'lock_key': string,
              'actions': [{
                  'action': ('put', 'delete'),
                  'id': user-defined-record-id,
                  'hash': user-defined-hash,
              }],
          }
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    actions = request.json_body.get('actions')
    if actions is None:
        raise HTTPBadRequest("No actions specified")

    for entry in actions:
        action = entry.get('action')
        if action is None:
            raise HTTPBadRequest("No action specified in %s" % repr(entry))
        elif action not in ['put', 'delete']:
            raise HTTPBadRequest("Unknown action %s" % repr(action))
        record_id = entry.get('id')
        if record_id is None:
            raise HTTPBadRequest("No record id specified in %s" % repr(entry))
        entry['id'] = record_database.url_string_to_record_id(record_id)
        if action == 'put':
            if entry.get('hash') is None:
                raise HTTPBadRequest("No hash specified in %s" % repr(entry))
        else:
            if entry.get('hash') is not None:
                raise HTTPBadRequest("Unexpected hash for delete action in %s" % repr(entry))

    config = record_database.load_config_from_name(sync_name, 'server')
    for entry in actions:
        action = entry['action']
        record_id = entry['id']
        if action == 'put':
            record_database.insert_or_update_hash(config, section_name, record_id, entry['hash'])
        elif action == 'delete':
            record_database.delete_hash(config, section_name, record_id)
        else:
            assert False
    return {}


@view_config(route_name='delete_hash', renderer='json')
def delete_hash_view(request):
    '''
    DELETE /{name}/{section}/{id}/hash
        < {'lock_key': string}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_hash(config, section_name, record_id)
    return {}


@view_config(route_name='get_record_and_hash', renderer='json')
def get_record_and_hash_view(request):
    '''
    GET /{name}/{section}/{id}/record-hash
        < {}
        > {'record': user-defined-record, 'hash': user-defined-hash}
        > raises 404
    '''
    sync_name = request.matchdict['name']
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    record = record_database.get_record(config, section_name, record_id)
    hash = record_database.get_hash(config, section_name, record_id)
    if (record is None) or (hash is None):
        raise NotFound
    return {'record': record, 'hash': hash}


@view_config(route_name='put_record_and_hash', renderer='json')
def put_record_and_hash_view(request):
    '''
    PUT /{name}/{section}/{id}/record-hash
        < {'lock_key': string, 'record': user-defined-record, 'hash': user-defined-hash}
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")

    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    record = request.json_body.get('record')
    if record is None:
        raise HTTPBadRequest("No record specified")
    hash = request.json_body.get('hash')
    if hash is None:
        raise HTTPBadRequest("No hash specified")

    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.insert_or_update_record(config, section_name, record_id, record)
    record_database.insert_or_update_hash(config, section_name, record_id, hash)
    return {}


@view_config(route_name='delete_record_and_hash', renderer='json')
def delete_record_and_hash_view(request):
    '''
    DELETE /{name}/{section}/{id}/record-hash
        < {'lock_key': string}
        > {}
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    record_id = record_database.url_string_to_record_id(request.matchdict['id'])
    config = record_database.load_config_from_name(sync_name, 'server')
    record_database.delete_record(config, section_name, record_id)
    record_database.delete_hash(config, section_name, record_id)
    return {}


@view_config(route_name='put_records_and_hashes_for_section', renderer='json')
def put_records_and_hashes_for_section_view(request):
    '''
    PUT /{name}/{section}/record-hashes
        < {
              'lock_key': string,
              'actions': [{
                  'action': ('put', 'delete', 'delete-record', 'delete-hash'),
                  'id': user-defined-record-id,
                  'record': user-defined-record,
                  'hash': user-defined-hash,
              }],
          }
        > {}
        > raises 400: HTTPBadRequest
        > raises 423: DatabaseLocked
    '''
    sync_name = request.matchdict['name']
    key = request.json_body.get('lock_key')
    if not Lock.test_lock(sync_name, key):
        raise DatabaseLocked("You do not own the lock on the database, or have the wrong key")
    section_name = request.matchdict['section']
    actions = request.json_body.get('actions')
    if actions is None:
        raise HTTPBadRequest("No actions specified")

    for entry in actions:
        action = entry.get('action')
        if action is None:
            raise HTTPBadRequest("No action specified in %s" % repr(entry))
        elif action not in ['put', 'delete', 'delete-record', 'delete-hash']:
            raise HTTPBadRequest("Unknown action %s" % repr(action))
        record_id = entry.get('id')
        if record_id is None:
            raise HTTPBadRequest("No record id specified in %s" % repr(entry))
        entry['id'] = record_database.url_string_to_record_id(record_id)
        if action == 'put':
            if (entry.get('record') is None) and (entry.get('hash') is None):
                raise HTTPBadRequest("No hash or record specified in %s" % repr(entry))
        else:
            if entry.get('record') is not None:
                raise HTTPBadRequest("Unexpected record for delete action in %s" % repr(entry))
            if entry.get('hash') is not None:
                raise HTTPBadRequest("Unexpected hash for delete action in %s" % repr(entry))

    config = record_database.load_config_from_name(sync_name, 'server')
    for entry in actions:
        action = entry['action']
        record_id = entry['id']
        if action == 'put':
            record = entry.get('record')
            hash = entry.get('hash')
            if record is not None:
                record_database.insert_or_update_record(config, section_name, record_id, record)
            if hash is not None:
                record_database.insert_or_update_hash(config, section_name, record_id, hash)
        elif action == 'delete':
            record_database.delete_record(config, section_name, record_id)
            record_database.delete_hash(config, section_name, record_id)
        elif action == 'delete-record':
            record_database.delete_record(config, section_name, record_id)
        elif action == 'delete-hash':
            record_database.delete_hash(config, section_name, record_id)
        else:
            assert False
    return {}


@view_config(route_name='server_status', renderer='json')
def server_status_view(request):
    return {'result': 'OK'}
