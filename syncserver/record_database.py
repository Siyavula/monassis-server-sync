DATABASE_REGISTRY = {
    'bookdb': {
        'module': 'monassis.books.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
    'historydb': {
        'module': 'monassis.historyservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
    'templatedb': {
        'module': 'monassis.qnxmlservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
    'userdb': {
        'module': 'monassis.usermanagement.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
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
        if ',' in section['id_column']:
            id_columns = [table.c[_.strip()] for _ in section['id_column'].split(',')]
        else:
            id_columns = [table.c[section['id_column']]]
        section['_id_columns'] = id_columns
        hash_columns = [table.c[column_name] for column_name in section['hash_columns']]
        section['_hash_columns'] = hash_columns

    return config


def get_all_hashes_for(sync_name=None, config=None):
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
