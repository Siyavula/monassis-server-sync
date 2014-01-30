# encoding: utf-8
from __future__ import division

if __name__ == '__main__':
    import core

    import sys, os, copy
    import requests, json
    import sqlalchemy
    from base64 import b64decode

    here = os.path.dirname(os.path.realpath(__file__))
    configName = sys.argv[1]

    # Load config and adjust for client side
    config = core.load_config(os.path.join(here, 'config', configName + '.ini'))
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        section['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[section['merge']]
    request = {'config': copy.deepcopy(config)}

    # Load database models
    core.load_config_databases(config)

    # Read last set of hashes from cache
    hashPath = os.path.join(here, 'hash_cache', configName + '.py')
    oldHashes = core.get_hashes_from_cache(hashPath)
    # Delete any old sections, in case config has changed
    for key in set(oldHashes.keys()) - set(config['sync:main']['sections']):
        del oldHashes[key]

    # Compute our new hashes
    newHashes = core.compute_hashes_from_database(config)

    # Compute our hash actions to get from old to new hashes
    hashActions = {}
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        if section['merge'] == 'slave':
            oldDict = oldHashes.get(sectionName, {})
            oldKeys = set(oldDict.keys())
            newDict = newHashes[sectionName]
            newKeys = set(newDict.keys())
            hashActions[sectionName] = {
                'insert': dict([(ident, newDict[ident]) for ident in newKeys - oldKeys]),
                'update': dict([(ident, newDict[ident]) for ident in newKeys.intersection(oldKeys) if newDict[ident] != oldDict[ident]]),
                'delete': list(oldKeys - newKeys),
            }
        else:
            raise Exception, "Hash update strategy %s in section %s not implemented"%(repr(section['merge']), repr(sectionName))

    # Make sync request to server
    url = config['sync:main']['url']
    request.update({
        'hash-actions': core.actions_to_json(hashActions),
        'data-actions': core.actions_to_json({}),
        'hash-hash': core.hash_hash_structure(newHashes),
    })
    print 'SYNC REQUEST to ' + url + ' <> ' + repr(request)
    response = requests.post(url, data=json.dumps(request))
    response = json.loads(response.content)
    print 'SYNC RESPONSE <> ' + repr(response)

    dataActions = core.actions_from_json(response['data-actions'])

    # Apply insert actions to our database
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        base64Columns = section.get('base64_encode', [])
        insertActions = dataActions[sectionName]['insert']
        for ident, values in insertActions.iteritems():
            print 'INSERT <> ' + repr({'table': section['_table'].name, 'id': ident})
            insertValues = dict([(section['_idColumns'][index].name, ident[index]) for index in range(len(section['_idColumns']))])
            for i in range(len(section['_hashColumns'])):
                column = section['_hashColumns'][i]
                key = column.name
                value = b64decode(values[i]) if key in base64Columns else values[i]
                insertValues[key] = value
            section['_table'].insert().values(**insertValues).execute()

    # Apply update actions to our database
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        base64Columns = section.get('base64_encode', [])
        updateActions = dataActions[sectionName]['update']
        for ident, values in updateActions.iteritems():
            print 'UPDATE <> ' + repr({'table': section['_table'].name, 'id': ident})
            updateValues = {}
            for i in range(len(section['_hashColumns'])):
                column = section['_hashColumns'][i]
                key = column.name
                value = b64decode(values[i]) if key in base64Columns else values[i]
                updateValues[key] = value
            whereClause = reduce(lambda x,y: x&y, [(section['_idColumns'][i] == ident[i]) for i in range(len(section['_idColumns']))])
            section['_table'].update().where(whereClause).values(**updateValues).execute()

    # Apply delete actions to our database (reversed to avoid problems with foreign key constraints)
    for sectionName in reversed(config['sync:main']['sections']):
        section = config['section:' + sectionName]
        deleteActions = dataActions[sectionName]['delete']
        for ident in deleteActions:
            print 'DELETE <> ' + repr({'table': section['_table'].name, 'id': ident})
            whereClause = reduce(lambda x,y: x&y, [(section['_idColumns'][i] == ident[i]) for i in range(len(section['_idColumns']))])
            section['_table'].delete().where(whereClause).execute()

    # Sanity check our updated hashes
    updatedHashes = core.compute_hashes_from_database(config)
    updatedHashesHash = core.hash_hash_structure(updatedHashes)
    assert updatedHashesHash == response['hash-hash']

    # Cache our hashes
    with open(hashPath, 'wt') as fp:
        fp.write(repr(updatedHashes))

    print 'DONE'
