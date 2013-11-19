# encoding: utf-8
from __future__ import division


DATABASE_REGISTRY = {
    'monassis.qnxmlservice': {
        'module': 'monassis.qnxmlservice.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
    'monassis.books': {
        'module': 'monassis.books.dbmodel',
        'version': 'DB_VERSION',
        'database': 'db',
        'tables': 'tables',
    },
}


def load_config(filename):
    import ConfigParser
    configParser = ConfigParser.SafeConfigParser()
    configParser.read(filename)
    config = {
        'name': configParser.get('sync', 'name'),
        'sections': [_.strip() for _ in configParser.get('sync', 'sections').split(',')], # Order matters because of foreign key constraints. Things get inserted in this order and then updated in this order and then deleted in the reverse order.
    }
    for section in configParser.sections():
        if section == 'sync':
            continue
        config[section] = dict(configParser.items(section))
        for key in 'hash_columns', 'base64_encode':
            if config[section].has_key(key):
                config[section][key] = [_.strip() for _ in config[section][key].split(',')]
    return config


def get_hashes_from_cache(filename):
    try:
        fp = open(filename, 'rt')
    except IOError:
        hashes = {}
    else:
        hashes = eval(fp.read())
        fp.close()
    return hashes


def load_config_databases(config):
    for sectionName in config['sections']:
        section = config[sectionName]
        databaseConfig = DATABASE_REGISTRY[section['database']]
        exec "import %s as dbmodel"%(databaseConfig['module'])
        version = eval('dbmodel.' + databaseConfig['version'])
        if version != config['database:' + section['database']]['version']:
            raise ValueError, "Database version number mismatch (db: %s, config: %s)."%(version, config['database:' + section['database']]['version'])
        section['_version'] = version
        database = eval('dbmodel.' + databaseConfig['database'])
        section['_database'] = database
        table = eval('dbmodel.' + databaseConfig['tables'])[section['table']]
        section['_table'] = table
        idColumn = table.c[section['id_column']]
        section['_idColumn'] = idColumn
        hashColumns = [table.c[columnName] for columnName in section['hash_columns']]
        section['_hashColumns'] = hashColumns


def compute_hashes_from_database(config):
    import sqlalchemy
    hashes = {}
    for sectionName in config['sections']:
        section = config[sectionName]
        select = sqlalchemy.sql.select([
            section['_idColumn'],
            sqlalchemy.func.md5(
                sqlalchemy.func.concat(*(
                    [sqlalchemy.sql.cast(column, sqlalchemy.Text()) + "," for column in section['_hashColumns']])))])
        result = section['_database'].execute(select)
        hashes[sectionName] = dict([(row[0], row[1]) for row in result])
        result.close()
    return hashes


def hash_hash_structure(struct):
    import hashlib
    return hashlib.md5(repr(sorted([((x.encode('utf-8') if isinstance(x, basestring) else x), sorted([((y.encode('utf-8') if isinstance(y, basestring) else y), (z.encode('utf-8') if isinstance(z, basestring) else z)) for y, z in subDict.items()])) for x, subDict in struct.items()]))).hexdigest()
