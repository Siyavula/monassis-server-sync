DATABASE_REGISTRY = {
    'bookdb': {
        'module': 'monassis.books.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'hashes',
    },
    'historydb': {
        'module': 'monassis.historyservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'hashes',
    },
    'templatedb': {
        'module': 'monassis.qnxmlservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'hashes',
    },
    'userdb': {
        'module': 'monassis.usermanagement.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'hashes',
    },
}


def load_config(filename):
    # Load config from file
    import ConfigParser
    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(filename)
    config = dict([(section, dict(config_parser.items(section))) for section in config_parser.sections()])
    make_list = lambda x: [_.strip() for _ in x.split(',')]
    config['sync:main']['sections'] = make_list(config['sync:main']['sections'])
    for key, value in config.iteritems():
        if key[:8] == 'section:':
            for key in ['hash_columns', 'base64_encode']:
                if value.has_key(key):
                    value[key] = make_list(value[key])

    # Load database objects and embed in config object
    for section_name in config['sync:main']['sections']:
        section = config['section:' + section_name]
        database_config = DATABASE_REGISTRY[section['database']]
        exec "import %s as dbmodel"%(database_config['module'])
        version = eval('dbmodel.' + database_config['version'])
        if version != config['database:' + section['database']]['version']:
            raise ValueError, "Database version number mismatch (db: %s, config: %s)."%(version, config['database:' + section['database']]['version'])
        section['_version'] = version
        database = eval('dbmodel.' + database_config['database'])
        section['_database'] = database
        table = eval('dbmodel.' + database_config['tables'])[section['table']]
        section['_table'] = table
        section['_hash_table'] = eval('dbmodel.' + database_config['tables'])[database_config['tables']]
        if ',' in section['id_column']:
            id_columns = [table.c[_.strip()] for _ in section['id_column'].split(',')]
        else:
            id_columns = [table.c[section['id_column']]]
        section['_id_columns'] = id_columns
        hash_columns = [table.c[column_name] for column_name in section['hash_columns']]
        section['_hash_columns'] = hash_columns

    return config


""" # This might be handy for populating record_hashes table initially
def get_all_hashes_for(sync_name=None, config=None, section=None):
    '''
    > {section_name: {ident: hash}}
    '''
    if config is None:
        import os
        configPath = os.path.join('config', sync_name + '.ini')
        config = load_config(configPath)

    import sqlalchemy
    hashes = {}
    for section_name in config['sync:main']['sections']:
        section = config['section:' + section_name]
        select = sqlalchemy.sql.select(
            section['_id_columns'] + [
                sqlalchemy.func.md5(
                    sqlalchemy.func.concat(*(
                        [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in section['_hash_columns']])))])
        result = section['_database'].execute(select)
        hashes[section_name] = dict([(tuple(row)[:-1], tuple(row)[-1]) for row in result])
        result.close()
    return hashes
"""


def pack_record_id(columns):
    # TODO
    return packed_string


def unpack_record_id(packed_string):
    # TODO
    return columns


def get_hash_actions_for(sync_name=None, config=None, section=None):
    if config is None:
        assert sync_name is not None
        import os
        configPath = os.path.join('config', sync_name + '.ini')
        config = load_config(configPath)
    else:
        sync_name = config['sync:main']['name']

    if section is None:
        sections = config['sync:main']['sections']
    elif isinstance(section, list) or isinstance(section, tuple):
        sections = section
    else:
        sections = [section]

    import sqlalchemy

    hash_actions = {}
    for section_name is sections:
        section = config['section:' + section_name]
        record_table = section['_table']
        hash_table = section['_hash_table']
        id_columns = section['_id_columns']
        data_columns = section['_hash_columns']
        record_id = sqlalchemy.func.concat(*(
            [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in id_columns]))
        record_hash = sqlalchemy.func.md5(
            sqlalchemy.func.concat(*(
                [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in data_columns])))

        # {id: ('insert', hash) / ('update', hash) / ('delete',)}
        hash_actions[section_name] = {}

        # New records in table, not yet in hash table
        # SELECT records.ids, MD5(records.data) FROM records LEFT OUTER JOIN (SELECT * FROM hashes WHERE sync_name = 'sync_name' AND section_name = 'section_name') h ON (CONCAT(records.ids::TEXT) = h.record_id) WHERE h.record_id IS NULL;
        select_hash = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).alias('h')
        select = sqlalchemy.sql.select(id_columns + [record_hash], select_hash.c.record_id == None).select_from(record_table.join(select_hash, select_hash.c.record_id == record_id, isouter=True))
        result = database.execute(select)
        hash_actions[section_name].update(dict([(tuple(row)[:-1], ('insert', tuple(row)[-1])) for row in result]))
        result.close()

        # Deleted records, but still in hash table
        # SELECT hashes.record_id FROM hashes LEFT OUTER JOIN records ON (CONCAT(records.ids::TEXT) = hashes.record_id) WHERE records.id1 IS NULL AND hashes.sync_name = 'sync_name' AND hashes.section_name = 'section_name';
        select = sqlalchemy.sql.select([hash_table.c.record_id], (id_columns[0] == None) & (hash_table.c.sync_name = sync_name) & (hash_table.c.section_name == section_name)).select_from(hash_table.join(record_table, hash_table.c.record_id == record_id, isouter=True))
        result = database.execute(select)
        hash_actions[section_name].update(dict([(unpack_record_id(row[0]), ('delete',)) for row in result]))
        result.close()

        # Changed records
        # SELECT records.ids, MD5(records.data) FROM records, hashes WHERE hashes.sync_name = 'sync_name' AND hashes.section_name = 'section_name' AND CONCAT(records.ids::TEXT) = hashes.record_id AND MD5(records.data) != hashes.record_hash;
        select = sqlalchemy.sql.select(id_columns + [record_hash], (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name) & (hash_table.c.record_id == record_id) & (hash_table.c.record_hash != record_hash));
        result = database.execute(select)
        hash_actions[section_name].update(dict([(tuple(row)[:-1], ('update', tuple(row)[-1])) for row in result]))
        result.close()

    return hash_actions


def get_record(sync_name, section, record_id):
    '''
    > {key: value}
    > None
    '''
    # TODO
    return None


def insert_or_update_record(sync_name, section, record_id, record):
    '''
    > hash
    '''
    # TODO
    pass


def delete_record(sync_name, section, record_id):
    '''
    '''
    # TODO
    pass
