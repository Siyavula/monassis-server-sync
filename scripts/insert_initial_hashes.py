if __name__ == '__main__':
    import sys, datetime
    from syncserver import record_database, utils

    # Load config and adjust for client side
    config_path = sys.argv[1]
    config = record_database.load_config_from_file(config_path, 'client', run_setup=True, sync_time=utils.now_utc())
    sync_name = record_database.get_config_sync_name(config)
    section_names = record_database.get_config_section_names(config)

    # Compute client hash actions and insert into hash table
    client_hash_actions = record_database.get_hash_actions(config)
    fp = open('insert_initial_hashes.out', 'wt')
    for section_name in section_names:
        for record_id, action in client_hash_actions[section_name]:
            assert action[0] == 'insert'
            record_database.insert_hash(config, section_name, record_id, action[1])
            fp.write(repr({'section_name': section_name, 'record_id': record_id, 'hash': action[1]}) + '\n')
    fp.close()
