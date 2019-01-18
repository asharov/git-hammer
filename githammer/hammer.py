import datetime
import os
import re
from collections import deque
from operator import itemgetter

from globber import globber
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from .combinedcommit import _iter_combined_commits
from .countdict import add_count_dict, subtract_count_dict
from .dbtypes import Author, Base, Commit, AuthorCommitDetail, Repository
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
    return f"{commit.author.name} <{commit.author.email}>"


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


class Hammer:

    def _build_repository_map(self, session):
        self.repositories = {}
        for dbrepo in session.query(Repository):
            self.repositories[dbrepo.repository_path] = dbrepo

    def _build_author_map(self, session):
        self.names_to_authors = {}
        for dbauthor in session.query(Author):
            self.names_to_authors[dbauthor.canonical_name] = dbauthor
            for alias in dbauthor.aliases:
                self.names_to_authors[alias] = dbauthor

    def _build_commit_map(self, session):
        self.shas_to_commits = {}
        for dbcommit in session.query(Commit):
            self.shas_to_commits[dbcommit.hexsha] = dbcommit
        for db_detail in session.query(AuthorCommitDetail):
            self.shas_to_commits[db_detail.commit_id].line_counts[db_detail.author] = db_detail.line_count
            if db_detail.test_count:
                self.shas_to_commits[db_detail.commit_id].test_counts[db_detail.author] = db_detail.test_count

    def _blame_blob_into_line_counts(self, repository, commit_to_blame, path, line_counts, test_counts):
        if not _is_source_file(repository.configuration, path):
            return
        is_test_file = _is_test_file(repository.configuration, path)
        blame = repository.git_repository.blame(commit_to_blame, path, w=True)
        for commit, lines in blame:
            author = self.names_to_authors[_author_line(commit)]
            line_counts[author] = line_counts.get(author, 0) + len(lines)
            if is_test_file:
                for line in lines:
                    if re.search(repository.test_line_regex, line):
                        test_counts[author] = test_counts.get(author, 0) + 1

    def _make_full_commit_stats(self, repository, commit):
        line_counts = {}
        test_counts = {}
        for git_object in commit.tree.traverse(visit_once=True):
            if git_object.type != 'blob':
                continue
            self._blame_blob_into_line_counts(repository, commit, git_object.path, line_counts, test_counts)
        return line_counts, test_counts

    def _make_diffed_commit_stats(self, repository, current_commit, next_commit, next_commit_line_counts,
                                  next_commit_test_counts):
        diff_index = next_commit.diff(current_commit, w=True)
        current_files = set()
        next_files = set()
        for add_diff in diff_index.iter_change_type('A'):
            current_files.add(add_diff.b_path)
        for delete_diff in diff_index.iter_change_type('D'):
            next_files.add(delete_diff.a_path)
        for rename_diff in diff_index.iter_change_type('R'):
            current_files.add(rename_diff.b_path)
            next_files.add(rename_diff.a_path)
        for modify_diff in diff_index.iter_change_type('M'):
            current_files.add(modify_diff.b_path)
            next_files.add(modify_diff.a_path)
        next_line_counts = {}
        current_line_counts = {}
        next_test_counts = {}
        current_test_counts = {}
        for current_file in current_files:
            self._blame_blob_into_line_counts(repository, current_commit, current_file, current_line_counts,
                                              current_test_counts)
        for next_file in next_files:
            self._blame_blob_into_line_counts(repository, next_commit, next_file, next_line_counts, next_test_counts)
        line_difference = subtract_count_dict(current_line_counts, next_line_counts)
        line_counts = add_count_dict(next_commit_line_counts, line_difference)
        test_difference = subtract_count_dict(current_test_counts, next_test_counts)
        test_counts = add_count_dict(next_commit_test_counts, test_difference)
        return line_counts, test_counts

    def _add_author_alias_if_needed(self, repository, commit):
        author_line = _author_line(commit)
        if not self.names_to_authors.get(author_line):
            canonical_name = repository.git_repository.git.show(commit.hexsha, format='%aN <%aE>', no_patch=True)
            author = self.names_to_authors[canonical_name]
            author.aliases.append(author_line)
            self.names_to_authors[author_line] = author

    def _add_canonical_authors(self, repository, session):
        author_lines = repository.git_repository.git.log(format='%aN <%aE>')
        for author_line in set(author_lines.splitlines()):
            if not self.names_to_authors.get(author_line):
                author = Author(canonical_name=author_line, aliases=[])
                self.names_to_authors[author_line] = author
                session.add(author)

    def _add_commit_object(self, repository, commit, session):
        self._add_author_alias_if_needed(repository, commit)
        author_line = _author_line(commit)
        author = self.names_to_authors[author_line]
        commit_object = Commit(
            hexsha=commit.hexsha, author=author, commit_time=commit.authored_datetime, parent_ids=[])
        if len(commit.parents) <= 1:
            if len(commit.parents) == 1:
                diff_stat = repository.git_repository.git.diff(
                    commit.parents[0], commit, numstat=True)
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
        self.shas_to_commits[commit.hexsha] = commit_object
        session.add(commit_object)

    def _add_commit_line_counts(self, commit, line_counts, test_counts, session):
        self.shas_to_commits[commit.hexsha].line_counts = line_counts
        self.shas_to_commits[commit.hexsha].test_counts = test_counts
        for author, count in line_counts.items():
            detail = AuthorCommitDetail(
                author_name=author.canonical_name, commit_id=commit.hexsha, line_count=count)
            if test_counts.get(author):
                detail.test_count = test_counts[author]
            session.add(detail)

    def _iter_branch(self, repository):
        commits = []
        commit_id = repository.head_commit_id
        while commit_id:
            commit = self.shas_to_commits.get(commit_id)
            if commit:
                commits.append(commit)
                commit_id = commit.parent_ids[0] if commit.parent_ids else None
            else:
                break
        return reversed(commits).__iter__()

    def __init__(self, project_name, database_server_url='postgresql+psycopg2://localhost/'):
        start_time = datetime.datetime.now()
        database_name = 'git-hammer-' + project_name
        engine = create_engine(database_server_url + database_name, use_batch_mode=True)
        if not database_exists(engine.url):
            create_database(engine.url)
            Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        session = self.Session()
        self._build_repository_map(session)
        self._build_author_map(session)
        self._build_commit_map(session)
        session.close()
        print('Init time {}'.format(datetime.datetime.now() - start_time))

    def add_repository(self, repository_path, configuration_file_path=None):
        repository_path = os.path.abspath(repository_path)
        if not self.repositories.get(repository_path):
            if not configuration_file_path:
                configuration_file_path = os.path.join(repository_path, 'git-hammer-config.json')
            else:
                configuration_file_path = os.path.abspath(configuration_file_path)
            session = self.Session(expire_on_commit=False)
            dbrepo = Repository(repository_path=repository_path, configuration_file_path=configuration_file_path)
            self.repositories[repository_path] = dbrepo
            session.add(dbrepo)
            session.commit()

    def update_data(self):
        session = self.Session(expire_on_commit=False)
        for repository in self.repositories.values():
            print('Repository {}'.format(repository.repository_path))
            head_commit = repository.git_repository.head.commit
            if self.shas_to_commits.get(head_commit.hexsha):
                continue
            repository = session.merge(repository, load=False)
            start_time = datetime.datetime.now()
            self._add_canonical_authors(repository, session)
            self._add_commit_object(repository, head_commit, session)
            (head_line_counts, head_test_counts) = self._make_full_commit_stats(repository, head_commit)
            self._add_commit_line_counts(head_commit, head_line_counts, head_test_counts, session)
            repository.head_commit_id = head_commit.hexsha
            commits_to_process = deque([head_commit])
            commit_count = 1
            print('Commit {:>5}: {}'.format(
                commit_count, datetime.datetime.now() - start_time))
            while commits_to_process:
                current_commit = commits_to_process.popleft()
                current_commit_line_counts = self.shas_to_commits[current_commit.hexsha].line_counts
                current_commit_test_counts = self.shas_to_commits[current_commit.hexsha].test_counts
                for parent in reversed(current_commit.parents):
                    if not self.shas_to_commits.get(parent.hexsha):
                        self._add_commit_object(repository, parent, session)
                        parent_line_counts, parent_test_counts = self._make_diffed_commit_stats(
                            repository, parent, current_commit, current_commit_line_counts, current_commit_test_counts)
                        self._add_commit_line_counts(
                            parent, parent_line_counts, parent_test_counts, session)
                        commits_to_process.appendleft(parent)
                        commit_count += 1
                        if commit_count % 20 == 0:
                            print('Commit {:>5}: {}'.format(
                                commit_count, datetime.datetime.now() - start_time))
                    self.shas_to_commits[current_commit.hexsha].parent_ids.append(parent.hexsha)
            print('Commit processing time {}'.format(datetime.datetime.now() - start_time))
            _print_line_counts(self.shas_to_commits[head_commit.hexsha].line_counts)
        start_time = datetime.datetime.now()
        session.commit()
        print('Database commit time {}'.format(datetime.datetime.now() - start_time))

    def iter_authors(self):
        return set(self.names_to_authors.values()).__iter__()

    def iter_commits(self, **kwargs):
        iterators = [self._iter_branch(repository) for repository in self.repositories.values()]
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
        session = self.Session()
        for commit in session.query(Commit).order_by(Commit.commit_time):
            yield commit
        session.close()
