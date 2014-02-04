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
    config = record_database.load_config_from_file(configPath, 'client')
    sync_name = config['sync:main']['name']

    # Connect to sync server
    connected = False
    attempts = 0
    while not connected and (attempts < 5):
        try:
            sync_session = sync_api.SyncSession(sync_name, config['sync:main']['url'])
            connected = True
        except sync_api.DatabaseLocked:
            import time
            minutes = 2**attempts # Exponential back-off waiting time
            print 'Database locked, waiting %i minutes...'%(minutes)
            time.sleep(60 * minutes)
            attempts += 1
    if not connected:
        print 'Could not obtain database lock after max (%i) attempts'%(attempts)
        sys.exit(-1)

    # Check database consistency using hash_hash
    client_hash_hash = record_database.get_hash_hash(config=config)
    server_hash_hash = sync_session.get_hash_hash()
    if client_hash_hash != server_hash_hash:
        print 'Hash hash is inconsistent between client and server. Refusing to synchronise.'
        sys.exit(-1)

    import pdb
    pdb.set_trace()

    # Compute client hash actions to get from old to new hashes
    client_hash_actions = record_database.get_hash_actions(config=config)
    # Find out how hashes have changed on the server
    server_hash_actions = sync_session.get_hash_actions()

    sys.exit()

    # Figure out how to sync
    client_actions = {}
    server_actions = {}
    for section_name in config['sync:main']['sections']:
        merge_strategy = config['section:' + section_name]['merge']
        if merge_strategy == 'master':
            client_data_actions, server_data_actions = utils.sync_master_slave(client_hash_actions, server_hash_actions)
        elif merge_strategy == 'slave':
            server_data_actions, client_data_actions = utils.sync_master_slave(server_hash_actions, client_hash_actions)
        elif merge_strategy == 'parent':
            client_data_actions, server_data_actions = utils.sync_parent_child(client_hash_actions, server_hash_actions)
        elif merge_strategy == 'child':
            server_data_actions, client_data_actions = utils.sync_parent_child(server_hash_actions, client_hash_actions)
        else:
            Exception, "Unknown merge strategy: %s"%(repr(merge_strategy))

        # Aggregate actions by type
        for actions, data_actions in [(client_actions, client_data_actions), (server_actions, server_data_actions)]:
            actions[section_name] = {'insert': [], 'update': [], 'delete': []}
            for ident, action in data_actions.iteritems():
                actions[section_name][action].append(ident)

    # Apply inserts locally
    for section_name in config['sync:main']['sections']:
        for record_id in client_actions[section_name]['insert']:
            record = sync_session.get_record(section_name, record_id)
            # TODO: insert into table
            # TODO: insert into record_hash
        
    # Apply updates locally
    for section_name in config['sync:main']['sections']:
        for record_id in client_actions[section_name]['update']:
            record = sync_session.get_record(section_name, record_id)
            # TODO: update record in table
            # TODO: update record_hash
        
    # Apply deletes locally
    for section_name in config['sync:main']['sections']:
        for record_id in client_actions[section_name]['delete']:
            pass
            # TODO: delete record from table
            # TODO: delete record_hash
        
    # TODO: Send records to server
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
