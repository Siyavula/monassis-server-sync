from sqlalchemy import Column, Integer, String, DateTime, event
from sqlalchemy.exc import IntegrityError
import transaction

from syncserver.models.support import Base, DBSession
from syncserver.utils import now_utc, force_utc

from uuid import uuid4


class LockError(Exception):
    pass


class Lock(Base):
    __tablename__ = "lock"

    sync_name = Column(String, nullable=False)

    # SqlAlchemy ORM needs a primary key specified even if the table doesn't have one.
    key = Column(String, nullable=False, primary_key=True)
    locked_at = Column(DateTime(timezone=True), nullable=False)
    last_accessed_at = Column(DateTime(timezone=True), nullable=False)

    # The following is a dummy column that will always be set to 0.
    # This solves concurrency issues by never allowing more than one
    # row in the table.
    keep_unique = Column(Integer, unique=True, nullable=False, default=0)

    def __json__(self, request):
        return {
            'sync_name': self.sync_name,
            'key': self.key,
            'locked_at': self.locked_at.isoformat(),
            'last_accessed_at': self.last_accessed_at.isoformat(),
        }

    def __str__(self):
        return "<Lock by=%s, since=%s>" % (self.sync_name, self.locked_at.isoformat())

    @classmethod
    def obtain_lock(cls, sync_name):
        from datetime import timedelta
        now = now_utc()

        # Clear timed out lock (if any)
        DBSession.query(Lock).filter(Lock.last_accessed_at < now - timedelta(minutes=15)).delete()
        transaction.commit()

        # Set up new lock
        key = str(uuid4())
        lock = Lock()
        lock.sync_name = sync_name
        lock.key = key
        lock.locked_at = now
        lock.last_accessed_at = now

        # Try to create new lock
        try:
            DBSession.add(lock)
            transaction.commit()
        except IntegrityError:
            raise LockError("Already locked")
        else:
            return key

    @classmethod
    def test_lock(cls, sync_name, key):
        lock = DBSession.query(Lock).first()
        if (lock is not None) and (lock.sync_name == sync_name) and (lock.key == key):
            lock.last_accessed_at = now_utc()
            DBSession.add(lock)
            transaction.commit()
            return True
        else:
            return False

    @classmethod
    def release_lock(cls, sync_name, key):
        if not Lock.test_lock(sync_name, key):
            raise LockError("You do not have lock")
        else:
            DBSession.query(Lock).delete()
            transaction.commit()

    @classmethod
    def loaded(cls, target, context):
        # ensure timestamps have timezones (SQLite doesn't support timezones)
        target.locked_at = force_utc(target.locked_at)
        target.last_accessed_at = force_utc(target.last_accessed_at)


event.listen(Lock, 'load', Lock.loaded)
