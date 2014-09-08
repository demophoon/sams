import transaction

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    and_,
    or_,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
)

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class AdapterHelper(object):

    def __init__(self, adapter, monitor):
        self._adapter = adapter
        self._monitor = monitor

    def create_check(self, **kwargs):
        with transaction.manager:
            check = DBSession.query(Check).filter(
                Check.adapter == self._adapter,
                Check.monitor == self._monitor,
                Check.id == kwargs['id'],
            ).first()
            if check:
                return check
            check = Check(
                adapter=self._adapter,
                monitor=self._monitor,
                **kwargs
            )
            return check

    def query(self, obj):
        if obj == Check:
            return DBSession.query(Check).filter(
                Check.adapter == self._adapter,
                Check.monitor == self._monitor,
            )
        elif obj == History:
            return DBSession.query(History).join(Check).filter(
                Check.adapter == self._adapter,
                Check.monitor == self._monitor,
            )
        return DBSession.query(obj)


class Check(Base):
    __tablename__ = 'checks'
    guid = Column(Integer, primary_key=True)
    adapter = Column(Text)
    monitor = Column(Text)
    id = Column(Text)
    name = Column(Text)
    type = Column(Text)
    hostname = Column(Text)
    resolution = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    outages = relationship("History", backref="check")

    @property
    def status(self):
        current = DBSession.query(History).join(Check).filter(
            Check.guid == self.guid
        ).order_by(
            History.end.desc()
        ).first()
        if current:
            return current.status
        return "unknown"


class History(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('checks.guid'))
    status = Column(Text)
    start = Column(DateTime)
    end = Column(DateTime)
    updated_at = Column(DateTime)

    @hybrid_method
    def between(self, start, end):
        return or_(
            and_(History.start >= start, History.start <= end),
            and_(History.end >= start, History.end <= end),
            and_(History.start <= start, History.end >= end),
        )

    @hybrid_property
    def duration(self):
        return History.end - History.start


class Tag(Base):
    __tablename__ = 'tag'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
