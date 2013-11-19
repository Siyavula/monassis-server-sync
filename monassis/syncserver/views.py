# encoding: utf-8
from __future__ import division

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest, HTTPForbidden

import sqlalchemy
import logging

def tic():
    import time
    return time.time()

def toc(startTime, extraInfo=None):
    import time
    stopTime = time.time()
    import inspect
    log = logging.getLogger('tictoc')
    message = "%s took %.3es"%(inspect.stack()[1][3], stopTime-startTime)
    if extraInfo is not None:
        message += " [%s]"%extraInfo
    log.info(message)


@view_config(context=HTTPNotFound, renderer='templates/404.pt')
def not_found(self, request):
    try:
        userId, userSession = get_user_info(request)
        message = '''Got a 404 at URL %s
session: %s'''%(request.url, repr(userSession))
    except HTTPForbidden, e:
        message = 'Got an anonymous 404 at URL %s'%(request.url)

    log = logging.getLogger(__name__)
    log.warning(message)

    request.response.status_int = 404
    return {}


DATABASE_REGISTRY = {
    'monassis.qnxmlservice': {
        'module': 'monassis.qnxmlservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
    'monassis.books': {
        'module': 'monassis.books.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
}

def hash_struct(struct):
    import hashlib
    return hashlib.md5(repr(sorted([(key, sorted(value.items())) for key, value in struct.items()]))).hexdigest()

def get_data(section, idents):
    import copy
    columns = copy.copy(section['_hashColumns'])
    if section.has_key('base64_encode'):
        sectionColumns = section['hash_columns']
        for column in section['base64_encode']:
            index = sectionColumns.index(column)
            columns[index] = sqlalchemy.func.encode(columns[index], 'base64')
    select = sqlalchemy.sql.select([section['_idColumn']] + columns, section['_idColumn'].in_(idents))
    result = section['_database'].execute(select)
    return dict([(row[0], row[1:]) for row in result])

def sync_master_slave(request, config, oldHashes, ourNewHashes, theirNewHashes):
    # As master, we never have to update anything
    ourDataActions = {}

    # Compare hashes and determine merge actions
    ourKeys = set(ourNewHashes.keys())
    theirKeys = set(theirNewHashes.keys())
    theirDataActions = {
        'insert': get_data(config, list(ourKeys - theirKeys)),
        'update': get_data(config, [ident for ident in ourKeys.intersection(theirKeys) if ourNewHashes[ident] != theirNewHashes[ident]]),
        'delete': list(theirKeys - ourKeys),
    }

    return ourDataActions, theirDataActions

def sync_slave_master():
    pass

def sync_parent_child():
    '''
    # Compute our hash actions
    ourHashActions = {}
    for sectionName in ourNewHashes:
        oldDict = oldHashes.get(sectionName, {})
        oldKeys = set(oldDict.keys())
        newDict = ourNewHashes[sectionName]
        newKeys = set(newDict.keys())
        ourHashActions[sectionName] = {
            'insert': get_data(config[sectionName], list(newKeys - oldKeys)),
            'update': get_data(config[sectionName], [ident for ident in newKeys.intersection(oldKeys) if newDict[ident] != oldDict[ident]]),
            'delete': list(oldKeys - newKeys),
        }
    '''

def sync_child_parent():
    pass

def sync_peer_peer():
    pass

def update_hashes(hashes, hashActions):
    import copy
    newHashes = copy.copy(hashes)
    for sectionName, actions in hashActions.iteritems():
        d = newHashes.setdefault(sectionName, {})
        for action in ['insert', 'update']:
            d.update(actions[action])
    for sectionName, actions in hashActions.iteritems():
        d = newHashes[sectionName]
        for ident in actions['delete']:
            if ident in d:
                del d[ident]
            else:
                # TODO: return an error response here. should never exist a key in their hash table that was not in ours.
                assert False
    return newHashes

@view_config(route_name='sync', renderer='json')
def sync_view(request):
    tictoc = tic()

    import os, copy

    #syncRequest = request.json_body
    syncRequest = {
        'config': {
            'name': 'office-qa',
            'sections': ['books'],
            'books': {
                'database': 'monassis.books',
                'table': 'books',
                'id_column': 'id',
                'hash_columns': ['subject', 'grade', 'title'],
                'merge': 'slave',
            },
            'database:monassis.books': {
                'version': '1.4.3',
            },
        },
        'hash-actions': {
            'books': {
                'insert': {100: '0800fc577294c34e0b28ad2839435945'},
                'update': {},
                'delete': [100],
            },
        },
        'hash-hash': '76fe3afb02c89d5c39c269844670e56a',
    }
    #/syncRequest = request.json_body

    import ConfigParser
    configParser = ConfigParser.SafeConfigParser()
    configParser.read(
        os.path.join(
            request.registry.settings['config_path'],
            syncRequest['config']['name'] + '.ini'))
    config = {
        'name': configParser.get('sync', 'name'),
        'sections': [_.strip() for _ in configParser.get('sync', 'sections').split(',')], # Order matters because of foreign key constraints. Things get inserted in this order and then updated in this order and then deleted in the reverse order.
    }
    for section in configParser.sections():
        if section == 'sync':
            continue
        config[section] = dict(configParser.items(section))
        for key in 'hash_columns', 'base64_encode':
            if config[section].has_key(key):
                config[section][key] = [_.strip() for _ in config[section][key].split(',')]

    # Sanity check configurations
    for sectionName in syncRequest['config']['sections']:
        syncRequest['config'][sectionName]['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[syncRequest['config'][sectionName]['merge']]
    assert syncRequest['config'] == config # TODO: return error response

    # Load database models
    for sectionName in config['sections']:
        section = config[sectionName]
        databaseConfig = DATABASE_REGISTRY[section['database']]
        exec "import %s as dbmodel"%(databaseConfig['module'])
        version = eval('dbmodel.' + databaseConfig['version'])
        section['_version'] = version
        database = eval('dbmodel.' + databaseConfig['database'])
        section['_database'] = database
        table = eval('dbmodel.' + databaseConfig['tables'])[section['table']]
        section['_table'] = table
        idColumn = table.c[section['id_column']]
        section['_idColumn'] = idColumn
        hashColumns = [table.c[columnName] for columnName in section['hash_columns']]
        section['_hashColumns'] = hashColumns

    # Sanity check config database versions
    for sectionName in config['sections']:
        assert section['_version'] == config['database:' + section['database']]['version'] # TODO: return error response

    # Read last set of hashes from cache
    cachePath = request.registry.settings['cache_path']
    hashPath = os.path.join(cachePath, config['name'] + '.py')
    try:
        fp = open(hashPath, 'rt')
    except IOError:
        oldHashes = {}
    else:
        oldHashes = eval(fp.read())
        fp.close()
    # Delete any old sections, in case config has changed
    for key in set(oldHashes.keys()) - set(config['sections']):
        del oldHashes[key]

    # Apply their hash actions to old hashes to get their new hashes
    theirNewHashes = update_hashes(oldHashes, syncRequest['hash-actions'])
    theirNewHashesHash = hash_struct(theirNewHashes)
    if theirNewHashesHash != syncRequest['hash-hash']:
        # TODO: return an error response here. hashes should match post update
        assert False

    # Compute our new hashes
    ourNewHashes = {}
    for sectionName in config['sections']:
        section = config[sectionName]
        select = sqlalchemy.sql.select([
            section['_idColumn'],
            sqlalchemy.func.md5(
                sqlalchemy.func.concat(*(
                    [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in section['_hashColumns']])))])
        result = section['_database'].execute(select)
        ourNewHashes[sectionName] = dict([(row[0], row[1]) for row in result])

    ourDataActions = {}
    theirDataActions = {}
    for sectionName in config['sections']:
        if config[sectionName]['merge'] == 'master':
            ourDataActions[sectionName], theirDataActions[sectionName] = sync_master_slave(request, config[sectionName], oldHashes.get(sectionName, {}), ourNewHashes[sectionName], theirNewHashes.get(sectionName, {}))
        else:
            raise Exception, "Merge strategy %s in section %s not implemented"%(repr(config[sectionName]['merge']), repr(sectionName))

    '''
    # Apply our updates
    for sectionName in config['sections']:
        pass
    '''

    # Recompute hashes after updates
    finalHashes = {}
    for sectionName in config['sections']:
        if config[sectionName]['merge'] == 'master':
            finalHashes[sectionName] = ourNewHashes[sectionName]
        else:
            raise Exception, "Hash update strategy %s in section %s not implemented"%(repr(config[sectionName]['merge']), repr(sectionName))
    finalHashesHash = hash_struct(finalHashes)

    # Store new hashes in cache
    with open(hashPath, 'wt') as fp:
        fp.write(repr(finalHashes))

    response = {
        'data-actions': theirDataActions,
        'hash-hash': finalHashesHash,
    }

    toc(tictoc)
    return response
