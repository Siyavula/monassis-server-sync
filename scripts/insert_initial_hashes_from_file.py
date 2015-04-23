if __name__ == '__main__':
    import sys
    from syncserver import record_database, utils

    # Load config and adjust for client side
    config_path = sys.argv[1]
    config = record_database.load_config_from_file(
        config_path, 'client', run_setup=True, sync_time=utils.now_utc())
    sync_name = record_database.get_config_sync_name(config)
    section_names = record_database.get_config_section_names(config)

    # Compute client hash actions and insert into hash table
    fp = open(sys.argv[2], 'rt')
    while True:
        line = fp.readline().strip()
        if line == '':
            break
        entry = eval(line)
        record_database.insert_hash(
            config, entry['section_name'], entry['record_id'], entry['hash'])
