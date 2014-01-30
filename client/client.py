'''
Apply inserts locally
  GET /office-qa/records/section-name/id-columns {} -> {'record': {key: value}}
  Insert locally and compute hash
  Update remote hash: PUT /office-qa/hashes/section-name/id-columns {'lock_key': UUID, 'hash': UUID}
   - on network problems: retry
	 - on complete fail: delete local record and quit

Apply updates locally
  GET /office-qa/records/section-name/id-columns {} -> {'record': {key: value}}
  Remember and update/insert local record, if possible (unchanged and depending on merge strategy), and new hash
   - if changed: move on to next record
  Update remote hash: PUT /office-qa/hashes/section-name/id-columns {'lock_key': UUID, 'hash': UUID}
   - on network problems: retry
   - on complete fail (or hash mismatch which really shouldn't happen): roll back local record (unless it's been updated since remembering it) and quit

Apply deletes locally
  Delete remote hash: DELETE /office-qa/hashes/section-name/id-columns {'lock_key': UUID} -> {}
   - on network problems: retry
	 - on complete fail: quit
   - on success: delete local record

Apply inserts and updates remotely
  retrieve local record (we'll do the update/insert even if it has changed since sync start)
  PUT /office-qa/records/section-name/id-columns {'lock_key': UUID, 'record': {key: value}} -> {'hash': UUID}
    (this will also update the hash)
   - on network problems: retry
   - on complete fail: quit
	 - on hash mismatch, which really shouldn't happen: raise a huge exception

Apply deletes remotely
  DELETE /office-qa/records/section-name/id-columns {'lock_key': UUID} -> {}
    (this will also delete the hash)
   - on network problems: retry
   - on complete fail: quit

Remove my lock on the sync server
PUT /office-qa/unlock {'lock_key': UUID} -> {}
 -> locked by someone else
 -> now unlocked

Trigger client onchange events
'''

if __name__ == '__main__':
    import sys
    import sync_api
    from syncserver import record_database, utils

    # Load config and adjust for client side
    configPath = sys.argv[1]
    config = record_database.load_config(configPath)
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
        section['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[section['merge']]
    sync_name = config['sync:main']['name']

    # Connect to sync server
    session = sync_api.SyncSession(sync_name, config['sync:main']['url'])
    # TODO: Might raise sync_api.DatabaseLocked

    # Get last hashes from server
    old_hashes = session.get_hashes()
    # Find out how hashes have changed on the server
    server_hash_actions = session.get_hash_actions()
    # Compute new hashes on server
    server_new_hashes = utils.apply_hash_actions(old_hashes, server_hash_actions)
    # Compute new hashes on client
    client_new_hashes = record_database.get_all_hashes_for(config=config)
    # Compute client hash actions to get from old to new hashes
    client_hash_actions = utils.compute_hash_actions(old_hashes, client_new_hashes)

    # TODO: Figure out how to sync
    sys.exit()

    #import requests, json
    #import sqlalchemy
    #from base64 import b64decode


    # Make sync request to server
    url = config['sync:main']['url']
    request.update({
        'hash-actions': core.actions_to_json(client_hash_actions),
        'data-actions': core.actions_to_json({}),
        'hash-hash': core.hash_hash_structure(client_new_hashes),
    })
    print 'SYNC REQUEST to ' + url + ' <> ' + repr(request)
    response = requests.post(url, data=json.dumps(request))
    response = json.loads(response.content)
    print 'SYNC RESPONSE <> ' + repr(response)

    dataActions = core.actions_from_json(response['data-actions'])

    # Apply insert actions to our database
    for section_name in config['sync:main']['sections']:
        section = config['section:' + section_name]
        base64Columns = section.get('base64_encode', [])
        insertActions = dataActions[section_name]['insert']
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
    for section_name in config['sync:main']['sections']:
        section = config['section:' + section_name]
        base64Columns = section.get('base64_encode', [])
        updateActions = dataActions[section_name]['update']
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
    for section_name in reversed(config['sync:main']['sections']):
        section = config['section:' + section_name]
        deleteActions = dataActions[section_name]['delete']
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
