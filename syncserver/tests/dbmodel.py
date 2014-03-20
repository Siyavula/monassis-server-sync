import sqlalchemy

DB_VERSION = '1.0'

# Determine which database to use from configuration file
import ConfigParser
parser = ConfigParser.SafeConfigParser()
parser.read('database.cfg')
try:
    dbUri = parser.get('databases', 'nosetests')
except ConfigParser.Error:
    db = None
else:
    dbmsName = dbUri[:dbUri.find(':')]
    db = sqlalchemy.create_engine(dbUri)
    metadata = sqlalchemy.MetaData(db)
    tables = {}


def create(**columns):
    global tables
    return tables['sessions'].insert().values(**columns).execute().inserted_primary_key[0]
        

def read(id):
    global db, tables
    select = sqlalchemy.sql.select([tables['records']], tables['records'].c.id == id)
    result = db.execute(select)
    row = result.fetchone()
    result.close()
    return row
        

def update(id, **columns):
    global tables
    tables['records'].update().where(tables['records'].c.id == id).values(**columns).execute()


def delete(id):
    global tables
    tables['records'].delete().where(tables['records'].c.id == id).execute()


def make_empty_db():
    global tables, metadata

    tables['records'] = sqlalchemy.Table(
        'records', metadata,
        sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column('column1', sqlalchemy.String),
        sqlalchemy.Column('column2', sqlalchemy.String),
        sqlalchemy.Column('column3', sqlalchemy.String),
    )

    from monassis.database import make_record_hash_table
    tables['record_hashes'] = make_record_hash_table(metadata)

    for key in tables:
        tables[key].create()


def load_db():
    global tables, metadata
    try:
        for key in ['records', 'record_hashes']:
            tables[key] = sqlalchemy.Table(key, metadata, autoload=True)
    except sqlalchemy.exc.NoSuchTableError:
        metadata.clear()
        make_empty_db()
