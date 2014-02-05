'''
Required generic structs:
  config

Required json-ready structs:
  record-id: tuple of str
  record: tuple
  hash: string
  hash-hash: string
  client-vars: dict

Required methods:
  load_config_from_file(config_path, role, run_setup=False, sync_time=None, client_vars=None)
   < config_path: str
   < role: 'client' or 'server'
   < run_setup: bool
   < sync_time: datetime.datetime
   < client_vars: user-defined-client-vars
   - if run_setup: sync_time will be set and client_vars might be set
   - if not run_setup: sync_time and client_vars will not be set
   > user-defined-config

  load_config_from_name(sync_name, role, run_setup=False, sync_time=None, client_vars=None)
   < sync_name: str
   for the rest, see load_config_from_file

  get_config_sync_name(config)
   < config: user-defined-config
   > str

  get_config_sync_url(config)
   < config: user-defined-config
   > str

  get_config_section_names(config)
   < config: user-defined-config
   > list of str

  get_config_merge_strategy_for_section(config, section_name)
   < config: user-defined-config
   < section_name: str
   > 'master' or 'slave' or 'parent' or 'child'

  get_config_sync_time(config)
   < config: user-defined-config
   > datetime.datetime

  get_config_client_vars(config)
   < config: user-defined-config
   > user-defined-client-vars

  get_hash_hash(config)
   < config: user-defined-config
   > user-defined-hash-hash

  get_hash_actions(config)
   < config: user-defined-config
   > {section_name [str]: [(user-defined-record-id, ('insert', user-defined-hash) or ('update', user-defined-hash, user-defined-hash) or ('delete', user-defined-hash))]}

  record_id_to_url_string(record_id)
   < record_id: user-defined_record_id
   > str

  url_string_to_record_id(string)
   < string: str
   > user-defined-record-id

  get_record(config, section_name, record_id)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   > user-defined-record

  get_record_and_compute_hash(config, section_name, record_id)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   > user-defined-record, user-defined-hash

  insert_record(config, section_name, record_id, record_data, volatile_hash=None)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_data: user-defined-record
   < volatile_hash: user-defined-record-hash

  update_record(config, section_name, record_id, record_data, volatile_hashes=None)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_data: user-defined-record
   < volatile_hashes: (user-defined-record-hash, user-defined-record-hash)

  insert_or_update_record(config, section_name, record_id, record_data)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_data: user-defined-record

  delete_record(config, section_name, record_id, volatile_hash=None)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < volatile_hash: user-defined-record-hash

  get_hash(config, section_name, record_id)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   > user-defined-hash

  insert_hash(config, section_name, record_id, record_hash)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_hash: user-defined-hash

  update_hash(config, section_name, record_id, record_hash)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_hash: user-defined-hash

  insert_or_update_hash(config, section_name, record_id, record_hash)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
   < record_hash: user-defined-hash

  delete_hash(config, section_name, record_id)
   < config: user-defined-config
   < section_name: str
   < record_id: user-defined-record-id
'''

__DATABASE_REGISTRY = {
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


def __setup_local_variables(config):
    from uuid import UUID
    import datetime
    return {
        'UUID': UUID,
        'datetime': datetime,
        'SYNC_TIME': config['sync:main']['sync_time'],
    }


def __eval_python_command(name, command, config):
    sql_results = []
    local_variables = config['_setup']
    local_variables['__sql_results'] = sql_results
    while True:
        start = command.find('`')
        if start == -1:
            break
        stop = command.find('`', start+1)
        if stop == -1:
            raise ValueError, "Unclosed back tick found in command %s"%(repr(command))
        sql = command[start+1:stop]
        sql_results.append(__eval_sql_command(name, sql, local_variables, config))
        command = command[:start] + '__sql_results[%i]'%(len(sql_results)-1) + command[stop+1:]
    local_variables[name] = eval(command, local_variables)


def __eval_sql_command(variable_name, sql, local_variables, config):
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
        else:
            config['_' + role + '_vars'].append(variable_name)
    exec "import " + __DATABASE_REGISTRY[database]['module'] + " as dbmodel"
    database = eval("dbmodel." + __DATABASE_REGISTRY[database]['database'])
    connection = database.connect()
    from sqlalchemy.sql import text
    result = connection.execute(text(sql), local_variables)
    return result
    

def load_config_from_file(config_path, role, run_setup=False, sync_time=None, client_vars=None):
    '''
    role: 'client' or 'server'
    '''
    # Load config from file
    import ConfigParser
    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(config_path)
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
    import sqlalchemy
    for section_name in config['sync:main']['sections']:
        section = config['section:' + section_name]
        database_config = __DATABASE_REGISTRY[section['database']]
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
            id_column_names = section['id_column'].split(',')
        else:
            id_column_names = [section['id_column']]
        id_columns = [sqlalchemy.sql.cast(table.c[column_name.strip()], sqlalchemy.Text()).label(column_name.strip()) for column_name in id_column_names]
        
        section['_id_columns'] = id_columns
        hash_columns = [table.c[column_name] for column_name in section['hash_columns']]
        section['_hash_columns'] = hash_columns

    # Adjust for role
    config['sync:main']['role'] = role
    if role == 'client':
        for sectionName in config['sync:main']['sections']:
            section = config['section:' + sectionName]
            section['merge'] = {'master': 'slave', 'slave': 'master', 'parent': 'child', 'child': 'parent', 'peer': 'peer'}[section['merge']]

    # Run setup
    if run_setup:
        config['sync:main']['sync_time'] = sync_time
        if client_vars is None:
            client_vars = {}
        else:
            client_vars = dict([(k, __json_to_struct(v)) for k, v in client_vars.iteritems()])
        commands = config.get('sync:setup')
        config['_setup'] = __setup_local_variables(config)
        if role == 'client':
            config['_client_vars'] = []
        else:
            config['_server_vars'] = []
        if commands is not None:
            for variable, command in commands:
                if (role == 'server') and (variable in client_vars.keys()):
                    config['_setup'][variable] = client_vars[variable]
                else:
                    __eval_python_command(variable, command, config)
        if role == 'client':
            config['_client_vars'] = list(set(config['_client_vars']))
        else:
            config['_server_vars'] = list(set(config['_server_vars']))

    return config


def load_config_from_name(sync_name, role, run_setup=False, sync_time=None, client_vars=None):
    '''
    role: 'client' or 'server'
    '''
    import os
    return load_config_from_file(os.path.join('config', sync_name + '.ini'), role, run_setup=run_setup, sync_time=sync_time, client_vars=client_vars)


def __struct_to_json(struct):
    import datetime
    from uuid import UUID
    if isinstance(struct, dict):
        raise TypeError, "Cannot automatically convert dict"
    elif isinstance(struct, list) or isinstance(struct, tuple):
        return [__struct_to_json(x) for x in struct]
    elif isinstance(struct, UUID):
        return repr(struct)
    elif isinstance(struct, datetime.datetime):
        return struct.isoformat()
    else:
        return struct


def __json_to_struct(json):
    import datetime
    from uuid import UUID
    if isinstance(json, list):
        return [__json_to_struct(x) for x in json]
    elif isinstance(json, basestring) and (json[:5] == 'UUID('):
        return eval(json)
    try:
        return datetime.datetime.strptime(json, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception:
        pass
    return json


def get_config_sync_name(config):
    return config['sync:main']['name']


def get_config_sync_url(config):
    return config['sync:main']['url']


def get_config_section_names(config):
    return config['sync:main']['sections']


def get_config_merge_strategy_for_section(config, section_name):
    return config['section:' + section_name]['merge']


def get_config_sync_time(config):
    return config['sync:main']['sync_time']


def get_config_client_vars(config):
    return dict([(key, __struct_to_json(config['_setup'][key])) for key in config['_client_vars']])


def __pack_record_id_values(values):
    return ''.join([str(v) + ',' for v in values])


def __unpack_record_id_values(values):
    return values.rstrip(',').split(',')


def __pack_record_id_values_sql(values):
    import sqlalchemy
    from uuid import UUID
    return sqlalchemy.func.concat(*([value + "," for value in values]))


def __pack_record_id_columns(columns):
    import sqlalchemy
    return sqlalchemy.func.concat(*([column + "," for column in columns]))


def __pack_record_hash_values(values):
    from hashlib import md5
    return md5(''.join([str(value) + ',' for value in values])).hexdigest()


def __pack_record_hash_values_sql(values):
    import sqlalchemy
    from uuid import UUID
    return sqlalchemy.func.md5(sqlalchemy.func.concat(*([sqlalchemy.sql.cast(str(value) if isinstance(value, UUID) else value, sqlalchemy.Text()) + "," for value in values])))


def __pack_record_hash_columns(columns):
    import sqlalchemy
    return sqlalchemy.func.md5(sqlalchemy.func.concat(*([sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in columns])))


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


def get_hash_actions(config, sections=None):
    import sqlalchemy, re

    sync_name = config['sync:main']['name']
    if sections is None:
        sections = config['sync:main']['sections']
    elif isinstance(section, list) or isinstance(section, tuple):
        sections = sections
    else:
        sections = [sections]

    local_variables = config['_setup']

    hash_actions = {}
    for section_name in sections:
        section = config['section:' + section_name]
        database = section['_database']
        record_table = section['_table']
        hash_table = section['_hash_table']
        id_columns = section['_id_columns']
        data_columns = section['_hash_columns']
        record_id = __pack_record_id_columns(id_columns)
        record_hash = __pack_record_hash_columns(data_columns)
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

        # [(record_id, ('insert', new_hash) or ('update', old_hash, new_hash) or ('delete', old_hash))]
        hash_actions[section_name] = []

        # New records in table, not yet in hash table
        # SELECT records.ids, MD5(records.data) FROM records LEFT OUTER JOIN (SELECT * FROM record_hashes WHERE sync_name = 'sync_name' AND section_name = 'section_name') h ON (CONCAT(records.ids::TEXT) = h.record_id) WHERE h.record_id IS NULL AND where_clause;
        select_hash = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).alias('h')
        full_where_clause = (select_hash.c.record_id == None)
        if where_clause is not None:
            full_where_clause = full_where_clause & where_clause
        select = sqlalchemy.sql.select(id_columns + [record_hash], full_where_clause).select_from(record_table.join(select_hash, select_hash.c.record_id == record_id, isouter=True))
        result = database.execute(select)
        hash_actions[section_name] += [(tuple(row)[:-1], ('insert', tuple(row)[-1])) for row in result]
        result.close()

        # Deleted records, but still in hash table
        # SELECT record_hashes.record_id, record_hashes.record_hash FROM record_hashes LEFT OUTER JOIN (SELECT * FROM users WHERE username < '14' AND username > '13') u ON (u.uuid::TEXT = record_hashes.record_id) WHERE u.uuid IS NULL AND record_hashes.sync_name = 'test' AND record_hashes.section_name = 'test';
        # SELECT record_hashes.record_id FROM record_hashes LEFT OUTER JOIN records ON (CONCAT(records.ids::TEXT) = record_hashes.record_id) WHERE records.id1 IS NULL AND record_hashes.sync_name = 'sync_name' AND record_hashes.section_name = 'section_name';
        if where_clause is not None:
            select_records = sqlalchemy.sql.select(id_columns, where_clause).alias('r')
            select_record_id = __pack_record_id_columns(select_records.c)
            select = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (tuple(select_records.c)[0] == None) & (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).select_from(hash_table.join(select_records, hash_table.c.record_id == select_record_id, isouter=True))
        else:
            select = sqlalchemy.sql.select([hash_table.c.record_id, hash_table.c.record_hash], (id_columns[0] == None) & (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name)).select_from(hash_table.join(record_table, hash_table.c.record_id == record_id, isouter=True))
        result = database.execute(select)
        hash_actions[section_name] += [(__unpack_record_id_values(row[0]), ('delete', row[1])) for row in result]
        result.close()

        # Changed records
        # SELECT records.ids, record_hashes.record_hash, MD5(records.data) FROM records, record_hashes WHERE record_hashes.sync_name = 'sync_name' AND record_hashes.section_name = 'section_name' AND CONCAT(records.ids::TEXT) = record_hashes.record_id AND MD5(records.data) != record_hashes.record_hash AND where_clause;
        full_where_clause = (hash_table.c.sync_name == sync_name) & (hash_table.c.section_name == section_name) & (hash_table.c.record_id == record_id) & (hash_table.c.record_hash != record_hash)
        if where_clause is not None:
            full_where_clause = full_where_clause & where_clause
        select = sqlalchemy.sql.select(id_columns + [hash_table.c.record_hash, record_hash], full_where_clause)
        result = database.execute(select)
        hash_actions[section_name] += [(tuple(row)[:-2], ('update',) + tuple(row)[-2:]) for row in result]
        result.close()

    return hash_actions


record_id_to_url_string = __pack_record_id_values


url_string_to_record_id = __unpack_record_id_values


def __base64_encode_record(record, section):
    base64_columns = section.get('base64_encode')
    if base64_columns is not None:
        from base64 import b64encode
        record = list(record)
        hash_columns = section['hash_columns']
        for column in base64_columns:
            index = hash_columns.index(column)
            record[index] = b64encode(record[index])
        record = tuple(record)
    return record


def __base64_decode_record(record, section):
    base64_columns = section.get('base64_encode')
    if base64_columns is not None:
        from base64 import b64decode
        record = list(record)
        hash_columns = section['hash_columns']
        for column in base64_columns:
            index = hash_columns.index(column)
            record[index] = b64decode(record[index])
        record = tuple(record)
    return record


def get_record(config, section_name, record_id):
    '''
    Retrieve row from records table.
    '''
    import sqlalchemy
    section = config['section:' + section_name]
    database = section['_database']
    id_columns = section['_id_columns']
    where_clause = reduce(lambda x, y: x & y, [id_columns[i] == record_id[i] for i in xrange(len(id_columns))])
    data_columns = section['_hash_columns']
    select = sqlalchemy.sql.select(data_columns, where_clause)
    result = database.execute(select)
    row = result.fetchone()
    result.close()
    if row is None:
        return None
    else:
        return __struct_to_json(__base64_encode_record(tuple(row), section))


def insert_record(config, section_name, record_id, record_data, volatile_hash=None):
    '''
    Insert into records table.
    '''
    import sqlalchemy

    # Setup for record insert
    section = config['section:' + section_name]
    record_table = section['_table']
    id_columns = section['_id_columns']
    data_columns = section['_hash_columns']
    record_values = {}
    for i in xrange(len(id_columns)):
        record_values[id_columns[i].name] = record_id[i]
    record_data = __base64_decode_record(__json_to_struct(record_data), section)
    for i in xrange(len(data_columns)):
        record_values[data_columns[i].name] = record_data[i]

    # Try to insert record
    try:
        record_table.insert().values(**record_values).execute()
    except sqlalchemy.exc.IntegrityError, error:
        if ('duplicate key' not in error.message) or (volatile_hash is None):
            # Treat as potentially volatile record only on duplicate key error
            # Reraise if the database is non-volatile
            raise error
        else:
            # Raise volatile exception if the database changed to
            # something we're not expecting
            if __compute_hash(config, section_name, record_id) != volatile_hash:
                from syncserver.errors import VolatileConflict
                raise VolatileConflict, "Tried to insert record, but found another, different record already there (section_name=%s, record_id=%s, record_data=%s)"%(repr(section_name), repr(record_id), repr(record_data))


def update_record(config, section_name, record_id, record_data, volatile_hashes=None):
    '''
    Update in records table.
    volatile_hashes: (old_hash, new_hash)
    returns number of rows updated
    '''
    # Setup for record update
    section = config['section:' + section_name]
    record_table = section['_table']
    data_columns = section['_hash_columns']
    record_data = __base64_decode_record(__json_to_struct(record_data), section)
    record_values = dict([(data_columns[i].name, record_data[i]) for i in xrange(len(data_columns))])
    id_columns = section['_id_columns']
    where_clause = reduce(lambda x, y: x & y, [id_columns[i] == record_id[i] for i in xrange(len(id_columns))])
    if volatile_hashes is not None:
        where_clause = where_clause & (__pack_record_hash_columns(data_columns) == volatile_hashes[0])

    # Try to update record
    affected_row_count = record_table.update().where(where_clause).values(**record_values).execute().rowcount
    if (affected_row_count == 0) and (volatile_hashes is not None):
        # Raise volatile exception if the database changed to
        # something we're not expecting
        h = __compute_hash(config, section_name, record_id)
        if h is None:
            from syncserver.errors import VolatileConflict
            raise VolatileConflict, "Tried to update record, but found that it had been deleted (section_name=%s, record_id=%s, record_data=%s)"%(repr(section_name), repr(record_id), repr(record_data))
        elif h != volatile_hashes[1]:
            from syncserver.errors import VolatileConflict
            raise VolatileConflict, "Tried to update record, but found that it had been updated to something else (section_name=%s, record_id=%s, record_data=%s)"%(repr(section_name), repr(record_id), repr(record_data))
        else:
            return 1 # Pretend that 1 row got updated since the new hashes match
    return affected_row_count


def insert_or_update_record(config, section_name, record_id, record_data):
    affected_rows = update_record(config, section_name, record_id, record_data)
    if affected_rows == 0:
        insert_record(config, section_name, record_id, record_data)


def delete_record(config, sync_name, section, record_id, volatile_hash=None):
    '''
    Delete from records table.
    '''
    section = config['section:' + section_name]
    record_table = section['_table']
    id_columns = section['_id_columns']
    where_clause = reduce(lambda x, y: x & y, [id_columns[i] == record_id[i] for i in xrange(len(id_columns))])
    if volatile_hash is not None:
        where_clause = where_clause & (__pack_record_hash_columns(section['_hash_columns']) == volatile_hash)

    # Try to delete record
    affected_row_count = record_table.delete().where(where_clause).execute().rowcount
    if (affected_row_count == 0) and (volatile_hash is not None):
        # Raise volatile exception if the database changed to
        # something we're not expecting
        if __compute_hash(config, section_name, record_id) is not None:
            from syncserver.errors import VolatileConflict
            raise VolatileConflict, "Tried to delete record, but found that it had been updated to something else (section_name=%s, record_id=%s, record_data=%s)"%(repr(section_name), repr(record_id), repr(record_data))
        else:
            return 1 # Pretend that 1 row got deleted since no rows match record_id
    return affected_row_count


def __compute_hash(config, section_name, record_id):
    '''
    Compute the hash of a given row from records table. This does
    *not* retrieve it from the record hashes table. See
    get_hash() for that.
    '''
    import sqlalchemy
    section = config['section:' + section_name]
    database = section['_database']
    id_columns = section['_id_columns']
    where_clause = reduce(lambda x, y: x & y, [id_columns[i] == record_id[i] for i in xrange(len(id_columns))])
    packed_record_hash_columns = __pack_record_hash_columns(section['_hash_columns'])
    select = sqlalchemy.sql.select([packed_record_hash_columns], where_clause)
    result = section['_database'].execute(select)
    row = result.fetchone()
    result.close()
    if row is None:
        return None
    else:
        return row[0]


def get_hash(config, section_name, record_id):
    '''
    Retrieve row from record hashes table.
    '''
    import sqlalchemy
    section = config['section:' + section_name]
    hash_table = section['_hash_table']
    packed_record_id_values = __pack_record_id_values_sql(record_id)
    select = sqlalchemy.sql.select([hash_table.c.record_hash], (hash_table.c.sync_name == config['sync:main']['name']) & (hash_table.c.section_name == section_name) & (hash_table.c.record_id == packed_record_id_values))
    result = section['_database'].execute(select)
    row = result.fetchone()
    result.close()
    if row is None:
        return None
    else:
        return row[0]


def insert_hash(config, section_name, record_id, record_hash):
    '''
    Insert into record hashes table.
    '''
    section = config['section:' + section_name]
    packed_record_id = __pack_record_id_values_sql(record_id)
    if record_hash is None:
        record_hash = __pack_record_hash_values_sql(record_data)
    section['_hash_table']\
        .insert()\
        .values(
            sync_name = config['sync:main']['name'],
            section_name = section_name,
            record_id = packed_record_id,
            record_hash = record_hash,
        )\
        .execute()


def update_hash(config, section_name, record_id, record_hash):
    '''
    Update record hashes table.
    '''
    section = config['section:' + section_name]
    hash_table = section['_hash_table']
    packed_record_id_values = __pack_record_id_values_sql(record_id)
    if record_hash is None:
        record_hash = __pack_record_hash_values_sql(record_data)
    affected_rows = hash_table.update()\
        .where(
            (hash_table.c.sync_name == config['sync:main']['name']) &\
            (hash_table.c.section_name == section_name) &\
            (hash_table.c.record_id == packed_record_id_values)
        )\
        .values(record_hash = record_hash)\
        .execute()\
        .rowcount
    return affected_rows


def insert_or_update_hash(config, section_name, record_id, record_hash):
    affected_rows = update_hash(config, section_name, record_id, record_hash)
    if affected_rows == 0:
        insert_hash(config, section_name, record_id, record_hash)


def delete_hash(config, section_name, record_id):
    '''
    Update record hashes table.
    '''
    section = config['section:' + section_name]
    hash_table = section['_hash_table']
    packed_record_id_values = __pack_record_id_values_sql(record_id)
    affected_rows = hash_table.delete()\
        .where(
            (hash_table.c.sync_name == config['sync:main']['name']) &\
            (hash_table.c.section_name == section_name) &\
            (hash_table.c.record_id == packed_record_id_values)
        )\
        .execute()\
        .rowcount
    return affected_rows


def get_record_and_compute_hash(config, section_name, record_id):
    import sqlalchemy
    section = config['section:' + section_name]
    database = section['_database']
    id_columns = section['_id_columns']
    where_clause = reduce(lambda x, y: x & y, [id_columns[i] == record_id[i] for i in xrange(len(id_columns))])
    data_columns = section['_hash_columns']
    packed_record_hash_columns = __pack_record_hash_columns(data_columns)
    select = sqlalchemy.sql.select(data_columns + [packed_record_hash_columns], where_clause)
    result = database.execute(select)
    row = result.fetchone()
    result.close()
    if row is None:
        return None, None
    else:
        row = tuple(row)
        return __struct_to_json(__base64_encode_record(row[:-1], section)), row[-1]
