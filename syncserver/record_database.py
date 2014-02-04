DATABASE_REGISTRY = {
    'bookdb': {
        'module': 'monassis.books.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'record_hashes',
    },
    'historydb': {
        'module': 'monassis.historyservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'record_hashes',
    },
    'templatedb': {
        'module': 'monassis.qnxmlservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'record_hashes',
    },
    'userdb': {
        'module': 'monassis.usermanagement.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
        'hash_table': 'record_hashes',
    },
}


def load_config_from_file(filename, role):
    '''
    role: 'client' or 'server'
    '''
    # Load config from file
    import ConfigParser
    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(filename)
    config = {}
    for section in config_parser.sections():
        if section == 'sync:setup':
            # Order of setup commands has to be preserved
            config[section] = config_parser.items(section)
        else:
            config[section] = dict(config_parser.items(section))
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
        section['_hash_table'] = eval('dbmodel.' + database_config['tables'])[database_config['hash_table']]
        if ',' in section['id_column']:
            id_columns = [table.c[_.strip()] for _ in section['id_column'].split(',')]
        else:
            id_columns = [table.c[section['id_column']]]
        section['_id_columns'] = id_columns
        hash_columns = [table.c[column_name] for column_name in section['hash_columns']]
        section['_hash_columns'] = hash_columns

    # Adjust for role
    config['sync:main']['role'] = role
    if role == 'client':
        for sectionName in config['sync:main']['sections']:
            section = config['section:' + sectionName]
            section['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[section['merge']]

    return config


def load_config_from_name(sync_name, role):
    '''
    role: 'client' or 'server'
    '''
    import os
    return load_config_from_file(os.path.join('config', sync_name + '.ini'))


""" # This might be handy for populating record_hashes table initially
def get_all_hashes_for(sync_name=None, config=None, section=None):
    '''
    > {section_name: {ident: hash}}
    '''
    if config is None:
        config = load_config_from_name(sync_name)

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


def get_hash_hash(config):
    import sqlalchemy
    from hashlib import md5
    sync_name = config['sync:main']['name']
    hash_hash = md5()
    for section_name in config['sync:main']['sections']:
        hash_hash.update(section_name)
        section = config['section:' + section_name]
        database = section['_database']
        hash_table = section['_hash_table']
        select = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).order_by(hash_table.c.record_id.asc())
        result = database.execute(select)
        for row in result:
            hash_hash.update(row['record_id'])
            hash_hash.update(row['record_hash'])
    return hash_hash.hexdigest()


def __setup_local_variables():
    from uuid import UUID
    import datetime
    return {
        'UUID': UUID,
        'datetime': datetime,
    }

def __eval_python_command(name, command, local_variables, config):
    sql_results = []
    local_variables['__sql_results'] = sql_results
    while True:
        start = command.find('`')
        if start == -1:
            break
        stop = command.find('`', start+1)
        if stop == -1:
            raise ValueError, "Unclosed back tick found in command %s"%(repr(command))
        sql = command[start+1:stop]
        sql_results.append(__eval_sql_command(sql, local_variables, config))
        command = command[:start] + '__sql_results[%i]'%(len(sql_results)-1) + command[stop+1:]
    local_variables[name] = eval(command, local_variables)


def __eval_sql_command(sql, local_variables, config):
    sql = sql.strip()
    if sql[0] != '{':
        raise ValueError, "No database specified for SQL command %s"%(repr(sql))
    stop = sql.find('}')
    if stop == -1:
        raise ValueError, "Unclosed brace in SQL command %s"%(repr(sql))
    database = sql[1:stop]
    sql = sql[stop+1:]
    if '.' in database:
        # client-only or server-only
        role, database = database.split('.')
        if role not in ['client', 'server']:
            raise ValueError, "Unknown role %s"%(repr(role))
        if role != config['sync:main']['role']:
            return []
    exec "import " + DATABASE_REGISTRY[database]['module'] + " as dbmodel"
    database = eval("dbmodel." + DATABASE_REGISTRY[database]['database'])
    connection = database.connect()
    from sqlalchemy.sql import text
    result = connection.execute(text(sql), local_variables)
    return result
    

def get_hash_actions(config, sections=None):
    import sqlalchemy, re

    sync_name = config['sync:main']['name']
    if sections is None:
        sections = config['sync:main']['sections']
    elif isinstance(section, list) or isinstance(section, tuple):
        sections = sections
    else:
        sections = [sections]


    # Do sync setup, if any
    commands = config.get('sync:setup')
    local_variables = __setup_local_variables()
    if commands is not None:
        for variable, command in commands:
            __eval_python_command(variable, command, local_variables, config)

    hash_actions = {}
    for section_name in sections:
        section = config['section:' + section_name]
        database = section['_database']
        record_table = section['_table']
        hash_table = section['_hash_table']
        id_columns = section['_id_columns']
        data_columns = section['_hash_columns']
        record_id = sqlalchemy.func.concat(*(
            [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in id_columns]))
        record_hash = sqlalchemy.func.md5(
            sqlalchemy.func.concat(*(
                [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in data_columns])))
        where_clause = section.get('where')
        if where_clause is not None:
            query_variables = dict(record_table.c)
            query_variables['__setup'] = local_variables
            offset = 0
            for match in re.finditer(r':[a-zA-Z_][a-zA-Z0-9_]*', where_clause):
                start, stop = match.span()
                where_clause = where_clause[:offset+start] + "__setup['" + where_clause[offset+start+1:offset+stop] + "']" + where_clause[offset+stop:]
                offset += 10 # len("__setup['']") - len(":")
            where_clause = eval(where_clause, query_variables, query_variables)

        # {id: ('insert', hash) / ('update', hash) / ('delete',)}
        hash_actions[section_name] = {}

        # New records in table, not yet in hash table
        # SELECT records.ids, MD5(records.data) FROM records LEFT OUTER JOIN (SELECT * FROM hashes WHERE sync_name = 'sync_name' AND section_name = 'section_name') h ON (CONCAT(records.ids::TEXT) = h.record_id) WHERE h.record_id IS NULL AND where_clause;
        select_hash = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).alias('h')
        full_where_clause = (select_hash.c.record_id == None)
        if where_clause is not None:
            full_where_clause = full_where_clause & where_clause
        select = sqlalchemy.sql.select(id_columns + [record_hash], full_where_clause).select_from(record_table.join(select_hash, select_hash.c.record_id == record_id, isouter=True))
        result = database.execute(select)
        hash_actions[section_name].update(dict([(tuple(row)[:-1], ('insert', tuple(row)[-1])) for row in result]))
        result.close()

        # Deleted records, but still in hash table
        # SELECT hashes.record_id FROM hashes LEFT OUTER JOIN records ON (CONCAT(records.ids::TEXT) = hashes.record_id) WHERE records.id1 IS NULL AND hashes.sync_name = 'sync_name' AND hashes.section_name = 'section_name';
        select = sqlalchemy.sql.select([hash_table.c.record_id], (id_columns[0] == None) & (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).select_from(hash_table.join(record_table, hash_table.c.record_id == record_id, isouter=True))
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
