# Copyright 2019 Jaakko Kangasharju
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import re

import git
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, orm
from sqlalchemy_utils import JSONType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData

from .config import Configuration


def _time_offset_to_local_time(time, offset):
    timezone = datetime.timezone(datetime.timedelta(seconds=offset))
    return time.replace(tzinfo=datetime.timezone.utc).astimezone(timezone)


_naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
_metadata = MetaData(naming_convention=_naming_convention)
Base = declarative_base(metadata=_metadata)


class Project(Base):
    __tablename__ = 'projects'

    project_name = Column(String, primary_key=True)


class Repository(Base):
    __tablename__ = 'repositories'

    id = Column(Integer, primary_key=True)
    repository_path = Column(String)
    configuration_file_path = Column(String)
    head_commit_id = Column(String, ForeignKey('commits.hexsha'))
    start_time = Column(DateTime())
    start_time_utc_offset = Column(Integer)

    head_commit = relationship('Commit', foreign_keys=[head_commit_id])

    def __init__(self, **kwargs):
        super(Repository, self).__init__(**kwargs)
        self._init_properties()

    @orm.reconstructor
    def _init_properties(self):
        self.configuration = Configuration(self.configuration_file_path)
        self.git_repository = git.Repo(self.repository_path)

    def start_time_tz(self):
        if self.start_time:
            return _time_offset_to_local_time(self.start_time, self.start_time_utc_offset)
        else:
            return None


class ProjectRepository(Base):
    __tablename__ = 'projectrepository'

    project_name = Column(String, ForeignKey('projects.project_name'), primary_key=True)
    repository_id = Column(String, ForeignKey('repositories.id'), primary_key=True)


class Author(Base):
    __tablename__ = 'authors'
    _name_regex = re.compile('^(.*)\\s+(<.*>)$')

    canonical_name = Column(String, primary_key=True)
    aliases = Column(JSONType)

    @property
    def name(self):
        match = Author._name_regex.match(self.canonical_name)
        if match:
            return match.group(1)
        else:
            return None

    def __eq__(self, other):
        return self.canonical_name == other.canonical_name and self.aliases == other.aliases

    def __hash__(self):
        return hash(self.canonical_name)

    def __repr__(self):
        return self.name


class Commit(Base):
    __tablename__ = 'commits'

    hexsha = Column(String, primary_key=True)
    author_name = Column(String, ForeignKey('authors.canonical_name'), nullable=False)
    added_lines = Column(Integer)
    deleted_lines = Column(Integer)
    commit_time = Column(DateTime(), nullable=False)
    commit_time_utc_offset = Column(Integer, nullable=False)
    parent_ids = Column(JSONType)
    repository_id = Column(Integer, ForeignKey('repositories.id'))

    author = relationship('Author', back_populates='commits', lazy='joined')

    def __init__(self, **kwargs):
        super(Commit, self).__init__(**kwargs)
        self._init_properties()

    @orm.reconstructor
    def _init_properties(self):
        self.line_counts = {}
        self.test_counts = {}

    def commit_time_tz(self):
        return _time_offset_to_local_time(self.commit_time, self.commit_time_utc_offset)


Author.commits = relationship('Commit', order_by=Commit.commit_time, back_populates='author')


class AuthorCommitDetail(Base):
    __tablename__ = 'authorcommit'

    author_name = Column(String, ForeignKey('authors.canonical_name'), primary_key=True)
    commit_id = Column(String, ForeignKey('commits.hexsha'), primary_key=True)
    line_count = Column(Integer, nullable=False)
    test_count = Column(Integer)

    author = relationship('Author')
    commit = relationship('Commit')
