from sqlalchemy import (
    Column,
    Integer,
    String,
    Index,
    )

from syncserver.models.support import Base, DBSession

class RecordHash(Base):
    __tablename__ = "hashes"

    id = Column(Integer, primary_key=True)
    sync_name = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False)
    record_id = Column(String, nullable=False)
    hash = Column(String, nullable=False)

    __table_args__ = (
        Index('uix_full_record_path', 'sync_name', 'section', 'record_id', unique=True),
    )

    def __json__(self, request):
        return {
            'id': self.id,
            'sync_name': self.sync_name,
            'section': self.section,
            'record_id': self.record_id,
            'hash': self.hash,
        }


    def __str__(self):
        return "<RecordHash id=%s, hash=%s>" % (self.id, self.hash)


    def update(self, hash):
        self.hash = hash
        DBSession.flush()


    @classmethod
    def get(cls, sync_name, section, record_id):
        query = DBSession.query(RecordHash).filter((sync_name == sync_name) & (section == section) & (record_id == record_id))
        try:
            return query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None


    @classmethod
    def get_by_id(cls, id):
        query = DBSession.query(RecordHash)
        return query.get(id)


    @classmethod
    def get_all_for(cls, sync_name):
        return DBSession.query(RecordHash).filter(sync_name == sync_name)


    @classmethod
    def create(cls, sync_name, section, record_id, hash):
        record_hash = RecordHash()
        record_hash.sync_name = sync_name
        record_hash.section = section
        record_hash.record_id = record_id
        record_hash.hash = hash
        DBSession.add(record_hash)
        DBSession.flush()
        return record_hash


    @classmethod
    def delete(cls, sync_name, section, record_id):
        DBSession.query(RecordHash).filter((sync_name == sync_name) & (section == section) & (record_id == record_id)).delete()
        DBSession.flush()
