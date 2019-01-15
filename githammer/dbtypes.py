import errno
import json
import re

import git
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, orm
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Repository(Base):
    __tablename__ = 'repositories'

    repository_path = Column(String, primary_key=True)
    configuration_file_path = Column(String)

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        self._init_properties()

    @orm.reconstructor
    def _init_properties(self):
        if self.configuration_file_path:
            try:
                fp = open(self.configuration_file_path, 'r')
            except OSError as error:
                if error.errno == errno.ENOENT:
                    self.configuration = {}
                else:
                    raise error
            else:
                self.configuration = json.load(fp)
        else:
            self.configuration = {}
        self.git_repository = git.Repo(self.repository_path)


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
    commit_time = Column(DateTime(timezone=True), nullable=False)
    parent_ids = Column(postgresql.ARRAY(String))

    author = relationship('Author', back_populates='commits')

    def __init__(self, **kwargs):
        super(Commit, self).__init__(**kwargs)
        self._init_properties()

    @orm.reconstructor
    def _init_properties(self):
        self.line_counts = {}


Author.commits = relationship('Commit', order_by=Commit.commit_time, back_populates='author')


class LineCount(Base):
    __tablename__ = 'linecounts'

    author_name = Column(String, ForeignKey('authors.canonical_name'), primary_key=True)
    commit_id = Column(String, ForeignKey('commits.hexsha'), primary_key=True)
    line_count = Column(Integer, nullable=False)

    author = relationship('Author')
    commit = relationship('Commit')
