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
import os
import io
import re
from operator import itemgetter

from globber import globber
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.exc import OperationalError

from .combinedcommit import _iter_combined_commits, CombinedCommit
from .countdict import add_count_dict, subtract_count_dict
from .dbtypes import Author, Base, Commit, AuthorCommitDetail, Repository, Project, ProjectRepository
from .frequency import Frequency

_diff_stat_regex = re.compile('^([0-9]+|-)\t([0-9]+|-)\t(.*)$')


def _matches_file_pattern(file, pattern):
    if type(pattern) is str:
        return globber.match(pattern, file)
    elif type(pattern) is list:
        return any(_matches_file_pattern(file, p) for p in pattern)
    else:
        raise TypeError('Pattern {} not list or string'.format(pattern))


def _is_source_file(configuration, path):
    source_files = configuration.get('sourceFiles')
    excluded_source_files = configuration.get('excludedSourceFiles')
    is_included = source_files is None or _matches_file_pattern(
        path, source_files)
    is_excluded = excluded_source_files is not None and _matches_file_pattern(
        path, excluded_source_files)
    return is_included and not is_excluded


def _is_test_file(configuration, path):
    test_files = configuration.get('testFiles')
    return test_files is not None and _matches_file_pattern(path, test_files)


def _print_line_counts(line_counts):
    for author, count in sorted(line_counts.items(), key=itemgetter(1), reverse=True):
        print('{:>10}  {}'.format(count, author.canonical_name))


def _author_line(commit):
    return '{} <{}>'.format(commit.author.name, commit.author.email)


def _start_of_interval(dt, frequency):
    if frequency is Frequency.daily:
        return datetime.datetime.combine(dt.date(), datetime.time(tzinfo=dt.tzinfo))
    elif frequency is Frequency.weekly:
        monday_dt = dt - datetime.timedelta(days=dt.weekday())
        return _start_of_interval(monday_dt, Frequency.daily)
    elif frequency is Frequency.monthly:
        first_dt = dt.replace(day=1)
        return _start_of_interval(first_dt, Frequency.daily)
    elif frequency is Frequency.yearly:
        january_dt = dt.replace(month=1)
        return _start_of_interval(january_dt, Frequency.monthly)


class DatabaseNotInitializedError(Exception):
    pass


class OldDatabaseSchemaError(Exception):
    pass


class Hammer:

    def _ensure_project_exists(self):
        if not database_exists(self._engine.url):
            create_database(self._engine.url)
            Base.metadata.create_all(self._engine)
        session = self._Session()
        if not session.query(Project).filter(Project.project_name == self.project_name).first():
            project = Project(project_name=self.project_name)
            session.add(project)
            session.commit()
        session.close()

    def _fail_unless_database_exists(self):
        if not database_exists(self._engine.url):
            raise DatabaseNotInitializedError('Database must be created for this operation')

    def _init_properties(self):
        self._repositories = []
        self._names_to_authors = {}
        self._shas_to_commits = {}

    def _commit_query(self, session):
        return session.query(Commit).join(Repository, Commit.repository_id == Repository.id).join(
            ProjectRepository).filter(ProjectRepository.project_name == self.project_name)

    def _build_repository_map(self, session):
        try:
            for dbrepo in session.query(Repository).join(ProjectRepository).filter(
                    ProjectRepository.project_name == self.project_name):
                self._repositories.append(dbrepo)
        except OperationalError:
            raise OldDatabaseSchemaError('Database created with too-old version of Git Hammer')

    def _build_author_map(self, session):
        for dbauthor in session.query(Author):
            self._names_to_authors[dbauthor.canonical_name] = dbauthor
            for alias in dbauthor.aliases:
                self._names_to_authors[alias] = dbauthor

    def _build_commit_map(self, session):
        for dbcommit in self._commit_query(session):
            self._shas_to_commits[dbcommit.hexsha] = dbcommit
        commits = self._commit_query(session).subquery()
        for db_detail in session.query(AuthorCommitDetail).join(commits):
            self._shas_to_commits[db_detail.commit_id].line_counts[db_detail.author] = db_detail.line_count
            if db_detail.test_count:
                self._shas_to_commits[db_detail.commit_id].test_counts[db_detail.author] = db_detail.test_count

    def _process_lines_into_line_counts(self, repository, commit, path, lines, line_counts, test_counts):
        is_test_file = _is_test_file(repository.configuration, path)
        author = self._names_to_authors[_author_line(commit)]
        line_counts[author] = line_counts.get(author, 0) + len(lines)
        if is_test_file:
            for line in lines:
                if re.search(repository.test_line_regex, line):
                    test_counts[author] = test_counts.get(author, 0) + 1

    def _blame_blob_into_line_counts(self, repository, commit_to_blame, path, line_counts, test_counts):
        if not _is_source_file(repository.configuration, path):
            return
        blame = repository.git_repository.blame(commit_to_blame, path, w=True)
        for commit, lines in blame:
            self._process_lines_into_line_counts(repository, commit, path, lines, line_counts, test_counts)

    def _make_full_commit_stats(self, repository, commit):
        line_counts = {}
        test_counts = {}
        for git_object in commit.tree.traverse(visit_once=True):
            if git_object.type != 'blob':
                continue
            if not _is_source_file(repository.configuration, git_object.path):
                continue
            lines = [line.decode('utf-8', 'ignore') for line in io.BytesIO(git_object.data_stream.read()).readlines()]
            self._process_lines_into_line_counts(repository, commit, git_object.path, lines, line_counts, test_counts)
        return line_counts, test_counts

    def _make_diffed_commit_stats(self, repository, commit, previous_commit, previous_commit_line_counts,
                                  previous_commit_test_counts):
        diff_index = previous_commit.diff(commit, w=True, ignore_submodules=True)
        current_files = set()
        previous_files = set()
        for add_diff in diff_index.iter_change_type('A'):
            current_files.add(add_diff.b_path)
        for delete_diff in diff_index.iter_change_type('D'):
            previous_files.add(delete_diff.a_path)
        for rename_diff in diff_index.iter_change_type('R'):
            current_files.add(rename_diff.b_path)
            previous_files.add(rename_diff.a_path)
        for modify_diff in diff_index.iter_change_type('M'):
            current_files.add(modify_diff.b_path)
            previous_files.add(modify_diff.a_path)
        previous_line_counts = {}
        current_line_counts = {}
        previous_test_counts = {}
        current_test_counts = {}
        for current_file in current_files:
            self._blame_blob_into_line_counts(repository, commit, current_file, current_line_counts,
                                              current_test_counts)
        for previous_file in previous_files:
            self._blame_blob_into_line_counts(repository, previous_commit, previous_file, previous_line_counts,
                                              previous_test_counts)
        line_difference = subtract_count_dict(current_line_counts, previous_line_counts)
        line_counts = add_count_dict(previous_commit_line_counts, line_difference)
        test_difference = subtract_count_dict(current_test_counts, previous_test_counts)
        test_counts = add_count_dict(previous_commit_test_counts, test_difference)
        return line_counts, test_counts

    def _add_author_alias_if_needed(self, repository, commit):
        author_line = _author_line(commit)
        if not self._names_to_authors.get(author_line):
            canonical_name = repository.git_repository.git.show(commit.hexsha, format='%aN <%aE>', no_patch=True)
            author = self._names_to_authors[canonical_name]
            author.aliases.append(author_line)
            self._names_to_authors[author_line] = author

    def _add_canonical_authors(self, repository, session):
        author_lines = repository.git_repository.git.log(format='%aN <%aE>')
        for author_line in set(author_lines.splitlines()):
            if not self._names_to_authors.get(author_line):
                author = Author(canonical_name=author_line, aliases=[])
                self._names_to_authors[author_line] = author
                session.add(author)

    def _add_commit_object(self, repository, commit, session):
        self._add_author_alias_if_needed(repository, commit)
        author_line = _author_line(commit)
        author = self._names_to_authors[author_line]
        commit_object = Commit(hexsha=commit.hexsha, author=author,
                               commit_time=commit.authored_datetime.astimezone(datetime.timezone.utc),
                               commit_time_utc_offset=int(commit.authored_datetime.utcoffset().total_seconds()),
                               parent_ids=[], repository_id=repository.id)
        if len(commit.parents) <= 1:
            if len(commit.parents) == 1:
                diff_stat = repository.git_repository.git.diff(
                    commit.parents[0], commit, numstat=True, ignore_submodules=True)
            else:
                diff_stat = repository.git_repository.git.show(commit, numstat=True, format='')
            added_lines = 0
            deleted_lines = 0
            for line in diff_stat.splitlines():
                match = re.fullmatch(_diff_stat_regex, line)
                if match:
                    if match.group(1) == '-' or match.group(2) == '-':
                        continue
                    if not _is_source_file(repository.configuration, match.group(3)):
                        continue
                    added_lines += int(match.group(1))
                    deleted_lines += int(match.group(2))
            commit_object.added_lines = added_lines
            commit_object.deleted_lines = deleted_lines
        self._shas_to_commits[commit.hexsha] = commit_object
        session.add(commit_object)

    def _add_commit_line_counts(self, commit, line_counts, test_counts, session):
        self._shas_to_commits[commit.hexsha].line_counts = line_counts
        self._shas_to_commits[commit.hexsha].test_counts = test_counts
        for author, count in line_counts.items():
            detail = AuthorCommitDetail(
                author_name=author.canonical_name, commit_id=commit.hexsha, line_count=count)
            if test_counts.get(author):
                detail.test_count = test_counts[author]
            session.add(detail)

    def _process_repository(self, repository, session):
        print('Repository {}'.format(repository.repository_path))
        repository = session.merge(repository, load=False)
        start_time = datetime.datetime.now()
        last_session_commit_time = start_time
        self._add_canonical_authors(repository, session)
        commit_count = 0
        for commit in self._iter_unprocessed_commits(repository):
            self._add_commit_object(repository, commit, session)
            if commit.parents:
                for parent in commit.parents:
                    self._shas_to_commits[commit.hexsha].parent_ids.append(parent.hexsha)
                parent_commit = self._shas_to_commits[commit.parents[0].hexsha]
                line_counts, test_counts = self._make_diffed_commit_stats(repository, commit, commit.parents[0],
                                                                          parent_commit.line_counts,
                                                                          parent_commit.test_counts)
            else:
                full_stats_start_time = datetime.datetime.now()
                line_counts, test_counts = self._make_full_commit_stats(repository, commit)
                print('Commit {} stats time: {}'.format(commit.hexsha,
                                                        datetime.datetime.now() - full_stats_start_time))
            self._add_commit_line_counts(commit, line_counts, test_counts, session)
            repository.head_commit_id = commit.hexsha
            commit_count += 1
            if commit_count % 20 == 0:
                print('Commit {:>5}: {}'.format(commit_count, datetime.datetime.now() - start_time))
            if datetime.datetime.now() - last_session_commit_time >= datetime.timedelta(minutes=5):
                session_commit_start_time = datetime.datetime.now()
                session.commit()
                print('Commit {:>5}: Database commit time {}'.format(commit_count,
                                                                     datetime.datetime.now() - session_commit_start_time))
                last_session_commit_time = datetime.datetime.now()
        print('Commit processing time {}'.format(datetime.datetime.now() - start_time))

    def _iter_branch(self, repository):
        commits = []
        commit_id = repository.head_commit_id
        while commit_id:
            commit = self._shas_to_commits.get(commit_id)
            if commit:
                commits.append(commit)
                commit_id = commit.parent_ids[0] if commit.parent_ids else None
            else:
                break
        return reversed(commits).__iter__()

    def _iter_unprocessed_commits(self, repository):
        for commit_id in repository.git_repository.git.log(reverse=True, date_order=True, format='%H').splitlines():
            if not self._shas_to_commits.get(commit_id):
                yield repository.git_repository.commit(commit_id)

    def __init__(self, project_name, database_url='sqlite:///git-hammer.sqlite'):
        start_time = datetime.datetime.now()
        self.project_name = project_name
        self._engine = create_engine(database_url)
        self._Session = sessionmaker(bind=self._engine)
        self._init_properties()
        if database_exists(self._engine.url):
            session = self._Session()
            self._build_repository_map(session)
            self._build_author_map(session)
            self._build_commit_map(session)
            session.close()
        print('Init time {}'.format(datetime.datetime.now() - start_time))

    def add_repository(self, repository_path, configuration_file_path=None):
        self._ensure_project_exists()
        repository_path = os.path.abspath(repository_path)
        if not next((repo for repo in self._repositories if repo.repository_path == repository_path), None):
            if not configuration_file_path:
                configuration_file_path = os.path.join(repository_path, 'git-hammer-config.json')
            else:
                configuration_file_path = os.path.abspath(configuration_file_path)
            session = self._Session(expire_on_commit=False)
            dbrepo = Repository(repository_path=repository_path, configuration_file_path=configuration_file_path)
            session.add(dbrepo)
            session.flush()
            self._repositories.append(dbrepo)
            project_repo = ProjectRepository(project_name=self.project_name, repository_id=dbrepo.id)
            session.add(project_repo)
            session.flush()
            self._process_repository(dbrepo, session)
            session.commit()

    def update_data(self):
        self._fail_unless_database_exists()
        session = self._Session(expire_on_commit=False)
        for repository in self._repositories:
            self._process_repository(repository, session)
        start_time = datetime.datetime.now()
        session.commit()
        print('Database commit time {}'.format(datetime.datetime.now() - start_time))

    def head_commit(self):
        self._fail_unless_database_exists()
        head_commit_ids = [repository.head_commit_id for repository in self._repositories]
        head_commits = [self._shas_to_commits[commit_id] for commit_id in head_commit_ids]
        return CombinedCommit(head_commits)

    def iter_all_project_names(self):
        self._fail_unless_database_exists()
        session = self._Session()
        for project in session.query(Project):
            yield project.project_name
        session.close()

    def iter_authors(self):
        self._fail_unless_database_exists()
        session = self._Session()
        for dbauthor in self._commit_query(session).join(Author).with_entities(Author).distinct():
            yield self._names_to_authors.get(dbauthor.canonical_name)
        session.close()

    def iter_commits(self, **kwargs):
        self._fail_unless_database_exists()
        iterators = [self._iter_branch(repository) for repository in self._repositories]
        commit_iterator = _iter_combined_commits(iterators)
        if not kwargs.get('frequency'):
            for commit in commit_iterator:
                yield commit
        else:
            next_commit_time = None
            for commit in commit_iterator:
                if not next_commit_time or commit.commit_time >= next_commit_time:
                    yield commit
                    start = _start_of_interval(commit.commit_time, kwargs['frequency'])
                    next_commit_time = kwargs['frequency'].next_instance(start)

    def iter_individual_commits(self):
        self._fail_unless_database_exists()
        session = self._Session()
        for commit in self._commit_query(session).order_by(Commit.commit_time):
            yield self._shas_to_commits.get(commit.hexsha)
        session.close()
