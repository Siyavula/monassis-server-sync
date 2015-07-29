from syncserver.db import tables
from siyavula.models.db import DBSession
from siyavula.models import Record

DB_VERSION = '1.0'


def create(**columns):
    return tables['records'].__table__.insert().values(**columns).execute().inserted_primary_key[0]


def read(id):
    return DBSession.query(Record).filter(Record.id == id)[0]


def update(id, **columns):
    tables['records'].__table__.update().where(tables['records'].c.id == id).values(
        **columns).execute()


def delete(id):
    tables['records'].__table__.delete().where(tables['records'].c.id == id).execute()
