if __name__ == '__main__':
    import sys, datetime
    import sync_api
    from syncserver import record_database, utils
    from syncserver.errors import VolatileConflict

    print 'Init'

    # Load config and adjust for client side
    config_path = sys.argv[1]
    config = record_database.load_config_from_file(config_path, 'client', run_setup=True, sync_time=utils.now_utc())
    sync_name = record_database.get_config_sync_name(config)
    section_names = record_database.get_config_section_names(config)

    # Connect to sync server
    connected = False
    attempts = 0
    while not connected and (attempts < 5):
        try:
            sync_session = sync_api.SyncSession(sync_name, record_database.get_config_sync_url(config))
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
    client_hash_hash = record_database.get_hash_hash(config)
    server_hash_hash = sync_session.get_hash_hash()
    if client_hash_hash != server_hash_hash:
        print 'Hash hash is inconsistent between client and server. Refusing to synchronise.'
        sys.exit(-1)

    print 'Compute hash actions'

    # Compute client hash actions to get from old to new hashes
    client_hash_actions = record_database.get_hash_actions(config)
    # Find out how hashes have changed on the server
    server_hash_actions = sync_session.get_hash_actions(record_database.get_config_sync_time(config), record_database.get_config_client_vars(config))

    for role, actions in [('client', client_hash_actions), ('server', server_hash_actions)]:
        print role
        for section_name in section_names:
            action_count = {'insert': 0, 'update': 0, 'delete': 0}
            for entry in actions[section_name]:
                action_count[entry[1][0]] += 1
            print '   %-20s -- insert: %4i, update: %4i, delete: %4i'%(section_name, action_count['insert'], action_count['update'], action_count['delete'])

    print 'Compute data actions'

    # Figure out how to sync
    client_actions = {}
    server_actions = {}
    for section_name in section_names:
        act = {'client': client_hash_actions[section_name], 'server': server_hash_actions[section_name]}
        for agent in ['client', 'server']:
            act[agent] = dict([(record_database.record_id_to_url_string(record_id), tuple(hash_action)) for record_id, hash_action in act[agent]])
        merge_strategy = record_database.get_config_merge_strategy_for_section(config, section_name)
        act['client'], act['server'] = utils.sync_on_strategy(merge_strategy, act['client'], act['server'])
        for agent in ['client', 'server']:
            act[agent] = [(record_database.url_string_to_record_id(record_id), data_action) for record_id, data_action in act[agent].iteritems()]
        client_actions[section_name] = act['client']
        server_actions[section_name] = act['server']

    def remote_hash_action(action, hash, section_name, record_id):
        # Will look up outside of function scope: record_database, sync_session
        if action is not None:
            packed_record_id = record_database.record_id_to_url_string(record_id)
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

    print 'Apply *-hash'

    # Apply hash-only actions for both client and server
    for source in [client_actions, server_actions]:
        for section_name in section_names:
            counter = 0
            for record_id, actions in source[section_name]:
                my_action = actions['our-action']
                if my_action[-5:] != '-hash':
                    continue
                new_hash = actions.get('new-hash')
                other_action = actions.get('their-action')
                if source == client_actions:
                    client_action = my_action
                    server_action = other_action
                else:
                    client_action = other_action
                    server_action = my_action
                remote_hash_action(server_action, new_hash, section_name, record_id)
                local_hash_action(client_action, new_hash, section_name, record_id)
                counter += 1
            if counter > 0:
                print '   %-20s -- %4i applied'%(section_name, counter)

    # TODO: Trigger client onchange events

    print 'Apply local insert'

    # Apply inserts locally
    for section_name in section_names:
        counter = 0
        for record_id, actions in client_actions[section_name]:
            if actions['our-action'] != 'insert':
                continue
            new_hash = actions['new-hash']
            server_action = actions.get('their-action')
            packed_record_id = record_database.record_id_to_url_string(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            remote_hash_action(server_action, new_hash, section_name, record_id)
            try:
                record_database.insert_record(config, section_name, record_id, record_data, volatile_hash=new_hash)
            except VolatileConflict:
                if record_database.get_config_merge_strategy_for_section(config, section_name) in ['slave', 'child']:
                    record_database.update_record(config, section_name, record_id, record_data)
            record_database.insert_hash(config, section_name, record_id, new_hash)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)

    print 'Apply local update'

    # Apply updates locally
    for section_name in section_names:
        counter = 0
        for record_id, actions in client_actions[section_name]:
            if actions['our-action'] != 'update':
                continue
            old_hash = actions['old-hash']
            new_hash = actions['new-hash']
            server_action = actions.get('their-action')
            packed_record_id = record_database.record_id_to_url_string(record_id)
            record_data = sync_session.get_record(section_name, packed_record_id)
            remote_hash_action(server_action, new_hash, section_name, record_id)
            try:
                record_database.update_record(config, section_name, record_id, record_data, volatile_hashes=(old_hash, new_hash))
            except VolatileConflict, error:
                if record_database.get_config_merge_strategy_for_section(config, section_name) in ['slave', 'child']:
                    if 'deleted' in error.message:
                        record_database.insert_record(config, section_name, record_id, record_data)
                    else:
                        assert 'updated' in error.message
                        record_database.update_record(config, section_name, record_id, record_data)
            record_database.update_hash(config, section_name, record_id, new_hash)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)
        
    print 'Apply local delete'

    # Apply deletes locally
    for section_name in section_names:
        counter = 0
        for record_id, actions in client_actions[section_name]:
            if actions['our-action'] != 'delete':
                continue
            old_hash = actions['old-hash']
            packed_record_id = record_database.record_id_to_url_string(record_id)
            server_action = actions.get('their-action')
            remote_hash_action(server_action, None, section_name, record_id)
            try:
                record_database.delete_record(config, section_name, record_id, volatile_hash=old_hash)
            except VolatileConflict:
                if record_database.get_config_merge_strategy_for_section(config, section_name) in ['slave', 'child']:
                    record_database.delete_record(config, section_name, record_id)
            record_database.delete_hash(config, section_name, record_id)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)
        
    print 'Apply remote insert'

    # Apply inserts remotely
    for section_name in section_names:
        counter = 0
        for record_id, actions in server_actions[section_name]:
            if actions['our-action'] != 'insert':
                continue
            new_hash = actions['new-hash']
            client_action = actions.get('their-action')
            record_data, volatile_hash = record_database.get_record_and_compute_hash(config, section_name, record_id)
            packed_record_id = record_database.record_id_to_url_string(record_id)
            if volatile_hash is None:
                # Record got deleted locally before we could insert it
                # remotely. Do nothing remotely since it doesn't exist
                # there. Delete local hash if necessary.
                if client_action != 'insert-hash':
                    local_hash_action('delete-hash', None, section_name, record_id)
            else:
                # If record got modified locally before we could
                # insert it remotely, just sent the new record and
                # update the local hash from the new record.
                sync_session.put_record_and_hash(section_name, packed_record_id, record_data, volatile_hash)
                if new_hash == volatile_hash:
                    local_hash_action(client_action, new_hash, section_name, record_id)
                else:
                    if client_action is None:
                        client_action = 'update-hash'
                    local_hash_action(client_action, volatile_hash, section_name, record_id)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)

    print 'Apply remote update'

    # Apply updates remotely
    for section_name in section_names:
        counter = 0
        for record_id, actions in server_actions[section_name]:
            if actions['our-action'] != 'update':
                continue
            new_hash = actions['new-hash']
            client_action = actions.get('their-action')
            record_data, volatile_hash = record_database.get_record_and_compute_hash(config, section_name, record_id)
            packed_record_id = record_database.record_id_to_url_string(record_id)
            if volatile_hash is None:
                # Record got deleted locally before we could update it
                # remotely. Delete it remotely and from the local hash
                # table.
                sync_session.delete_record_and_hash(section_name, packed_record_id)
                local_hash_action('delete-hash', None, section_name, record_id)
            else:
                # If record got modified locally before we could
                # update it remotely, just sent the new record and
                # update the local hash from the new record.
                sync_session.put_record_and_hash(section_name, packed_record_id, record_data, volatile_hash)
                if new_hash == volatile_hash:
                    local_hash_action(client_action, new_hash, section_name, record_id)
                else:
                    if client_action is None:
                        client_action = 'update-hash'
                    local_hash_action(client_action, volatile_hash, section_name, record_id)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)

    print 'Apply remote delete'

    # Apply deletes remotely.
    for section_name in section_names:
        counter = 0
        for record_id, actions in server_actions[section_name]:
            if actions['our-action'] != 'delete':
                continue
            client_action = actions.get('their-action')
            packed_record_id = record_database.record_id_to_url_string(record_id)
            sync_session.delete_record_and_hash(section_name, packed_record_id)
            local_hash_action(client_action, None, section_name, record_id)
            counter += 1
        if counter > 0:
            print '   %-20s -- %4i applied'%(section_name, counter)

    # Sanity check our updated hashes
    client_hash_hash = record_database.get_hash_hash(config)
    server_hash_hash = sync_session.get_hash_hash()
    if client_hash_hash != server_hash_hash:
        print 'Hash hash is inconsistent between client and server after sync. Will not be able to sync in future.'

    print 'DONE'
