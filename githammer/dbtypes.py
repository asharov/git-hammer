import re
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Author(Base):
    __tablename__ = 'authors'
    _name_regex = re.compile('^(.*)\\s+(<.*>)$')

    canonical_name = Column(String, primary_key=True)
    aliases = Column(postgresql.ARRAY(String))

    @property
    def name(self):
        match = Author._name_regex.match(self.canonical_name)
        if match:
            return match.group(1)
        else:
            return None

    def __repr__(self):
        return self.name


class Commit(Base):
    __tablename__ = 'commits'

    hexsha = Column(String, primary_key=True)
    author_name = Column(String, ForeignKey('authors.canonical_name'), nullable=False)
    added_lines = Column(Integer)
    deleted_lines = Column(Integer)
    commit_time = Column(DateTime, nullable=False)

    author = relationship('Author', back_populates='commits')

    def __init__(self, **kwargs):
        super(Commit, self).__init__(**kwargs)
        self.init_properties()

    @orm.reconstructor
    def init_properties(self):
        self.line_counts = {}


Author.commits = relationship('Commit', order_by=Commit.commit_time, back_populates='author')


class LineCount(Base):
    __tablename__ = 'linecounts'

    id = Column(Integer, primary_key=True)
    author_name = Column(String, ForeignKey('authors.canonical_name'), nullable=False)
    commit_id = Column(String, ForeignKey('commits.hexsha'), nullable=False)
    line_count = Column(Integer, nullable=False)

    author = relationship('Author')
    commit = relationship('Commit')
