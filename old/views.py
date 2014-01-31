# encoding: utf-8
from __future__ import division

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPBadRequest, HTTPForbidden

import sqlalchemy
import logging

import core

def get_data(section, idents):
    import copy
    hashColumns = copy.copy(section['_hashColumns'])
    if section.has_key('base64_encode'):
        sectionColumns = section['hash_columns']
        for column in section['base64_encode']:
            index = sectionColumns.index(column)
            hashColumns[index] = sqlalchemy.func.encode(hashColumns[index], 'base64').label('_' + column + '_base64_')
    allRows = {}
    blockSize = 1000
    for index in range(0, len(idents), blockSize):
        select = sqlalchemy.sql.select(section['_idColumns'] + hashColumns, sqlalchemy.tuple_(*(section['_idColumns'])).in_(idents[index:index+blockSize]))
        result = section['_database'].execute(select)
        allRows.update(dict([(tuple([row[column.name] for column in section['_idColumns']]), tuple([row[column.name] for column in hashColumns])) for row in result]))
        result.close()
    return allRows



@view_config(route_name='sync', renderer='json')
def sync_view(request):
    tictoc = tic()

    import os, copy

    # Read our and their configuration
    syncRequest = request.json_body
    config = core.load_config(
        os.path.join(
            request.registry.settings['config_path'],
            syncRequest['config']['sync:main']['name'] + '.ini'))

    # Revert sync request actions to dict
    for entry in ['hash-actions', 'data-actions']:
        if not syncRequest.has_key(entry):
            continue
        core.actions_from_json(syncRequest[entry])

    # Sanity check configurations
    for sectionName in syncRequest['config']['sync:main']['sections']:
        section = syncRequest['config']['section:' + sectionName]
        section['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[section['merge']]
    assert syncRequest['config'] == config # TODO: return error response

    # Load database models
    core.load_config_databases(config)

    # Read last set of hashes from cache
    cachePath = request.registry.settings['cache_path']
    hashPath = os.path.join(cachePath, config['sync:main']['name'] + '.py')
    oldHashes = core.get_hashes_from_cache(hashPath)
    # Delete any old sections, in case config has changed
    for key in set(oldHashes.keys()) - set(config['sync:main']['sections']):
        del oldHashes[key]

    # Apply their hash actions to old hashes to get their new hashes
    theirNewHashes = update_hashes(oldHashes, syncRequest['hash-actions'])
    theirNewHashesHash = core.hash_hash_structure(theirNewHashes)
    if theirNewHashesHash != syncRequest['hash-hash']:
        # TODO: return an error response here. hashes should match post update
        assert False

    # Compute our new hashes
    ourNewHashes = core.compute_hashes_from_database(config)

    # Determine what we have to do to update our and their data
    ourDataActions = {}
    theirDataActions = {}
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        if section['merge'] == 'master':
            ourDataActions[sectionName], theirDataActions[sectionName] = sync_master_slave(request, section, oldHashes.get(sectionName, {}), ourNewHashes[sectionName], theirNewHashes.get(sectionName, {}))
        else:
            raise Exception, "Merge strategy %s in section %s not implemented"%(repr(section['merge']), repr(sectionName))

    '''
    # Apply our updates
    for sectionName in config['sync:main']['sections']:
        pass
    '''

    # Recompute hashes after updates
    finalHashes = {}
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        if section['merge'] == 'master':
            finalHashes[sectionName] = ourNewHashes[sectionName]
        else:
            raise Exception, "Hash update strategy %s in section %s not implemented"%(repr(section['merge']), repr(sectionName))
    finalHashesHash = core.hash_hash_structure(finalHashes)

    # Store new hashes in cache
    with open(hashPath, 'wt') as fp:
        fp.write(repr(finalHashes))

    response = {
        'data-actions': core.actions_to_json(theirDataActions),
        'hash-hash': finalHashesHash,
    }

    toc(tictoc)
    return response
