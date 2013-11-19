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
    config = dict([(section, dict(configParser.items(section))) for section in configParser.sections()])
    make_list = lambda x: [_.strip() for _ in x.split(',')]
    config['sync:main']['sections'] = make_list(config['sync:main']['sections'])
    for key, value in config.iteritems():
        if key[:8] == 'section:':
            for key in ['hash_columns', 'base64_encode']:
                if value.has_key(key):
                    value[key] = make_list(value[key])
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
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
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
    for sectionName in config['sync:main']['sections']:
        section = config['section:' + sectionName]
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
