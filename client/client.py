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

    def remote_hash_action(action, hash, section_name, record_id):
        # Will look up outside of function scope: record_database, sync_session
        if action is not None:
            packed_record_id = record_database.pack_record_id(record_id)
            if action in ['insert-hash', 'update-hash']:
                assert hash is not None
                sync_session.put_hash(section_name, packed_record_id, hash)
            else:
                assert action == 'delete-hash'
                sync_session.delete_hash(section_name, packed_record_id)

    def local_hash_action(action, hash, section_name, record_id):
        # Will look up outside of function scope: record_database, config
        if action == 'insert-hash':
            assert hash is not None
            record_database.insert_hash(config, section_name, record_id, hash)
        elif action == 'update-hash':
            assert hash is not None
            record_database.update_hash(config, section_name, record_id, hash)
        elif action == 'delete-hash':
            record_database.delete_hash(config, section_name, record_id)
        else:
            assert action is None

    import pdb
    pdb.set_trace()

    # Apply hash-only actions for both client and server
    for source in [client_actions, client_actions]:
        for section_name in config['sync:main']['sections']:
            for record_id, actions in source[section_name].iteritems():
                my_action = actions['my-action']
                if my_action[-5:] != '-hash':
                    continue
                new_hash = actions.get('new-hash')
                other_action = actions.get('other-action')
                if source == client_actions:
                    client_action = my_action
                    server_action = other_action
                else:
                    client_action = other_action
                    server_action = my_action
                remote_hash_action(server_action, new_hash, section_name, record_id)
                local_hash_action(client_action, new_hash, section_name, record_id)

    # TODO: Trigger client onchange events

    # Apply inserts locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions['my-action'] != 'insert':
                continue
            new_hash = actions['new-hash']
            server_action = actions.get('other-action')
            packed_record_id = record_database.pack_record_id(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            remote_hash_action(server_action, new_hash, section_name, record_id)
            try:
                record_database.insert_record(config, section_name, record_id, record_data, volatile_hash=new_hash)
            except VolatileException:
                section = config['section:' + section_name]
                if section['merge'] in ['slave', 'child']:
                    record_database.update_record(config, section_name, record_id, record_data)
            record_database.insert_record_hash(config, section_name, record_id, record_hash=new_hash)

    # Apply updates locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions['my-action'] != 'update':
                continue
            old_hash = actions['old-hash']
            new_hash = actions['new-hash']
            server_action = actions.get('other-action')
            packed_record_id = record_database.pack_record_id(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            remote_hash_action(server_action, new_hash, section_name, record_id)
            try:
                record_database.update_record(config, section_name, record_id, record_data, volatile_hashes=(old_hash, new_hash))
            except VolatileException, error:
                section = config['section:' + section_name]
                if section['merge'] in ['slave', 'child']:
                    if 'deleted' in error.message:
                        record_database.insert_record(config, section_name, record_id, record_data)
                    else:
                        assert 'updated' in error.message
                        record_database.update_record(config, section_name, record_id, record_data)
            record_database.update_record_hash(config, section_name, record_id, record_hash=new_hash)
        
    # Apply deletes locally
    for section_name in config['sync:main']['sections']:
        for record_id, actions in client_actions[section_name].iteritems():
            if actions['my-action'] != 'delete':
                continue
            old_hash = actions['old-hash']
            packed_record_id = record_database.pack_record_id(record_id)
            server_action = actions.get('other-action')
            remote_hash_action(server_action, None, section_name, record_id)
            try:
                record_database.delete_record(config, section_name, record_id, volatile_hash=old_hash)
            except VolatileException:
                section = config['section:' + section_name]
                if section['merge'] in ['slave', 'child']:
                    record_database.delete_record(config, section_name, record_id, record_data)
            record_database.delete_record_hash(config, section_name, record_id)
        
    # Apply inserts and updates remotely. Still want to do inserts
    # before updates to maintain database integrity.
    for server_action in ['insert', 'update']:
        for section_name in config['sync:main']['sections']:
            for record_id, actions in server_actions[section_name].iteritems():
                if actions['my-action'] != server_action:
                    continue
                new_hash = actions['new-hash']
                client_action = actions.get('other-action')
                packed_record_id = record_database.pack_record_id(record_id)
                record_data = record_database.get_record(config, section_name, record_id)
                sync_session.put_record_and_hash(section_name, packed_record_id, record, new_hash)
                local_hash_action(client_action, new_hash, section_name, record_id)

    # Apply deletes remotely.
    for section_name in config['sync:main']['sections']:
        for record_id, actions in server_actions[section_name].iteritems():
            if actions['my-action'] != 'delete':
                continue
            client_action = actions.get('other-action')
            packed_record_id = record_database.pack_record_id(record_id)
            sync_session.delete_record_and_hash(section_name, packed_record_id)
            local_hash_action(client_action, None, section_name, record_id)

    # Sanity check our updated hashes
    client_hash_hash = record_database.get_hash_hash(config=config)
    server_hash_hash = sync_session.get_hash_hash()
    if client_hash_hash != server_hash_hash:
        print 'Hash hash is inconsistent between client and server after sync. Will not be able to sync in future.'

    print 'DONE'
