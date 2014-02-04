'''
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

Trigger client onchange events
'''

if __name__ == '__main__':
    import sys, datetime
    import sync_api
    from syncserver import record_database, utils

    # Load config and adjust for client side
    configPath = sys.argv[1]
    config = record_database.load_config_from_file(configPath, 'client', run_setup=True, sync_time=utils.now_utc())
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

    # Compute client hash actions to get from old to new hashes
    client_hash_actions = record_database.get_hash_actions(config)
    # Find out how hashes have changed on the server
    server_hash_actions = sync_session.get_hash_actions(config['sync:main']['sync_time'], dict([(key, config['_setup'][key]) for key in config['_client_vars']]))

    # Figure out how to sync
    client_actions = {}
    server_actions = {}
    for section_name in config['sync:main']['sections']:
        merge_strategy = config['section:' + section_name]['merge']
        if merge_strategy == 'master':
            client_data_actions, server_data_actions = utils.sync_master_slave(client_hash_actions[section_name], server_hash_actions[section_name])
        elif merge_strategy == 'slave':
            server_data_actions, client_data_actions = utils.sync_master_slave(server_hash_actions[section_name], client_hash_actions[section_name])
        elif merge_strategy == 'parent':
            client_data_actions, server_data_actions = utils.sync_parent_child(client_hash_actions[section_name], server_hash_actions[section_name])
        elif merge_strategy == 'child':
            server_data_actions, client_data_actions = utils.sync_parent_child(server_hash_actions[section_name], client_hash_actions[section_name])
        else:
            Exception, "Unknown merge strategy: %s"%(repr(merge_strategy))
        client_actions[section_name] = client_data_actions
        server_actions[section_name] = server_data_actions

    import pdb
    pdb.set_trace()

    # Apply hash-only actions
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            my_action = actions['my-action']
            if my_action[-5:] != '-hash':
                continue
            hash = actions['hash']
            other_action = actions.get('other-action')
            if other_action is not None:
                packed_record_id = record_database.pack_record_id(record_id)
                if other_action in ['insert-hash', 'update-hash']:
                    sync_session.put_hash(section_name, packed_record_id, hash)
                else:
                    assert other_action == 'delete-hash'
                    sync_session.delete_hash(section_name, packed_record_id)
            if my_action == 'insert-hash':
                record_database.insert_hash(config, section_name, record_id, hash)
            elif my_action == 'update-hash':
                record_database.update_hash(config, section_name, record_id, hash)
            else:
                assert my_action == 'delete-hash'
                record_database.delete_hash(config, section_name, record_id)

    # Apply inserts locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions['my-action'] != 'insert':
                continue
            hash = actions['hash']
            packed_record_id = record_database.pack_record_id(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            other_action = actions.get('other-action')
            if other_action is not None:
                if other_action in ['insert-hash', 'update-hash']:
                    sync_session.put_hash(section_name, packed_record_id, hash)
                else:
                    assert other_action == 'delete-hash'
                    sync_session.delete_hash(section_name, packed_record_id)
            try:
                record_database.insert_record(config, section_name, record_id, record_data, volatile=True, hash=hash)
            except VolatileException:
                record_database.insert_hash(config, section_name, record_id, hash)
        
    # Apply updates locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions[0] != 'update':
                continue
            hash = actions['hash']
            packed_record_id = record_database.pack_record_id(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            other_action = actions.get('other-action')
            if other_action is not None:
                if other_action in ['insert-hash', 'update-hash']:
                    sync_session.put_hash(section_name, packed_record_id, hash)
                else:
                    assert other_action == 'delete-hash'
                    sync_session.delete_hash(section_name, packed_record_id)
            try:
                record_database.update_record(config, section_name, record_id, record_data, volatile=True, hash=hash)
            except VolatileException:
                record_database.update_hash(config, section_name, record_id, hash)
        
    # Apply deletes locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions[0] != 'delete':
                continue
            packed_record_id = record_database.pack_record_id(record_id)
            other_action = actions.get('other-action')
            if other_action is not None:
                assert other_action == 'delete-hash'
                sync_session.delete_hash(section_name, packed_record_id)
            try:
                record_database.delete_record(config, section_name, record_id, volatile=True)
            except VolatileException:
                record_database.delete_hash(config, section_name, record_id)
        
    # TODO: Send records to server
    sys.exit()

    # Sanity check our updated hashes
    client_hash_hash = record_database.get_hash_hash(config=config)
    server_hash_hash = sync_session.get_hash_hash()
    if client_hash_hash != server_hash_hash:
        print 'Hash hash is inconsistent between client and server after sync. Will not be able to sync in future.'

    print 'DONE'
