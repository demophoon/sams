from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    ForeignKey,
)

from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship,
    )

from zope.sqlalchemy import ZopeTransactionExtension

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()


class Check(Base):
    __tablename__ = 'checks'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    type = Column(Text)
    hostname = Column(Text)
    resolution = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    outages = relationship("Outage", backref="check")


class Outage(Base):
    __tablename__ = 'outages'
    id = Column(Integer, primary_key=True)
    check_id = Column(Integer, ForeignKey('checks.id'))
    status = Column(Text)
    start = Column(DateTime)
    end = Column(DateTime)
    updated_at = Column(DateTime)
