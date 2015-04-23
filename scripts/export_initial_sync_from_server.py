'''
Set the server record hashes and dump to file the client record data
and hashes for the initial sync of a new client.
'''
if __name__ == '__main__':
    import sys
    import cPickle
    from syncserver import record_database, utils

    # Load config and adjust for client side
    config_path = sys.argv[1]
    config = record_database.load_config_from_file(
        config_path, 'server', run_setup=True, sync_time=utils.now_utc())
    sync_name = record_database.get_config_sync_name(config)
    section_names = record_database.get_config_section_names(config)

    # Compute client hash actions and insert into hash table
    client_hash_actions = record_database.get_hash_actions(config)

    # Sanity check that everything is an insert (the database should
    # be empty since this is the initial sync)
    for section_name in section_names:
        for record_id, action in client_hash_actions[section_name]:
            assert action[0] == 'insert'

    # Dump records and hashes to file for client and insert server hashes
    fp = open('export_initial_sync_from_server.pickle', 'wb')
    for section_name in section_names:
        for record_id, action in client_hash_actions[section_name]:
            record = record_database.get_record(config, section_name, record_id)
            struct = {
                'section_name': section_name,
                'record_id': record_id,
                'record': record,
                'hash': action[1],
            }
            cPickle.dump(struct, fp, protocol=2)
            record_database.insert_hash(config, section_name, record_id, action[1])
    fp.close()
