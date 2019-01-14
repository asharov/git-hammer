import datetime
import errno
import json
import os
import re
from collections import deque
from operator import itemgetter

import git
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from globber import matches_glob
from .countdict import add_count_dict, subtract_count_dict
from .dbtypes import Author, Base, Commit, LineCount
from .frequency import Frequency

_diff_stat_regex = re.compile('^([0-9]+|-)\t([0-9]+|-)\t(.*)$')


def _matches_file_pattern(file, pattern):
    if type(pattern) is str:
        return matches_glob(pattern, file)
    elif type(pattern) is list:
        return any(_matches_file_pattern(file, p) for p in pattern)
    else:
        raise TypeError('Pattern {} not list or string'.format(pattern))


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
            for line_count in session.query(LineCount).filter_by(commit_id=dbcommit.hexsha):
                dbcommit.line_counts[line_count.author] = line_count.line_count

    def _is_source_file(self, path):
        source_files = self.configuration.get('sourceFiles')
        excluded_source_files = self.configuration.get('excludedSourceFiles')
        is_included = source_files == None or _matches_file_pattern(
            path, source_files)
        is_excluded = excluded_source_files != None and _matches_file_pattern(
            path, excluded_source_files)
        return is_included and not is_excluded

    def _blame_blob_into_line_counts(self, commit_to_blame, path, line_counts):
        if not self._is_source_file(path):
            return
        blame = self.repository.blame(commit_to_blame, path, w=True)
        for commit, lines in blame:
            author = self.names_to_authors[_author_line(commit)]
            line_counts[author] = line_counts.get(author, 0) + len(lines)

    def _make_full_commit_stats(self, commit):
        line_counts = {}
        for object in commit.tree.traverse(visit_once=True):
            if object.type != 'blob':
                continue
            self._blame_blob_into_line_counts(
                commit, object.path, line_counts)
        return line_counts

    def _make_diffed_commit_stats(self, current_commit, next_commit, next_commit_stats):
        diff_index = next_commit.diff(current_commit)
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
        for current_file in current_files:
            self._blame_blob_into_line_counts(
                current_commit, current_file, current_line_counts)
        for next_file in next_files:
            self._blame_blob_into_line_counts(
                next_commit, next_file, next_line_counts)
        difference = subtract_count_dict(current_line_counts, next_line_counts)
        line_counts = add_count_dict(next_commit_stats, difference)
        return line_counts

    def _add_author_alias_if_needed(self, commit):
        author_line = _author_line(commit)
        if not self.names_to_authors.get(author_line):
            canonical_name = self.repository.git.show(commit.hexsha, format='%aN <%aE>', no_patch=True)
            author = self.names_to_authors[canonical_name]
            author.aliases.append(author_line)
            self.names_to_authors[author_line] = author

    def _add_canonical_authors(self, session):
        author_lines = self.repository.git.log(format='%aN <%aE>')
        for author_line in set(author_lines.splitlines()):
            if not self.names_to_authors.get(author_line):
                author = Author(canonical_name=author_line, aliases=[])
                self.names_to_authors[author_line] = author
                session.add(author)

    def _add_commit_object(self, commit, session):
        self._add_author_alias_if_needed(commit)
        author_line = _author_line(commit)
        author = self.names_to_authors[author_line]
        commit_object = Commit(
            hexsha=commit.hexsha, author=author, commit_time=commit.authored_datetime, parent_ids=[])
        if len(commit.parents) == 1:
            diff_stat = self.repository.git.diff(
                commit.parents[0], commit, numstat=True)
            added_lines = 0
            deleted_lines = 0
            for line in diff_stat.splitlines():
                match = re.fullmatch(_diff_stat_regex, line)
                if match:
                    if match.group(1) == '-' or match.group(2) == '-':
                        continue
                    if not self._is_source_file(match.group(3)):
                        continue
                    added_lines += int(match.group(1))
                    deleted_lines += int(match.group(2))
            commit_object.added_lines = added_lines
            commit_object.deleted_lines = deleted_lines
        self.shas_to_commits[commit.hexsha] = commit_object
        session.add(commit_object)

    def _add_commit_line_counts(self, commit, line_counts, session):
        self.shas_to_commits[commit.hexsha].line_counts = line_counts
        for author, count in line_counts.items():
            line_count = LineCount(
                author_name=author.canonical_name, commit_id=commit.hexsha, line_count=count)
            session.add(line_count)

    def __init__(self, repository_directory, name=None, configuration_file=None):
        self.repository_directory = os.path.abspath(repository_directory)
        if configuration_file == None:
            configuration_file = os.path.join(
                self.repository_directory, 'git-hammer-config.json')
        try:
            fp = open(configuration_file, 'r')
        except OSError as error:
            if error.errno == errno.ENOENT:
                self.configuration = {}
            else:
                raise error
        else:
            self.configuration = json.load(fp)
        self.repository = git.Repo(self.repository_directory)
        database_name = 'git-hammer-' + \
                        (name or os.path.basename(self.repository_directory))
        engine = create_engine(
            'postgresql://localhost/' + database_name, echo=True)
        if not database_exists(engine.url):
            create_database(engine.url)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        session = self.Session()
        self._build_author_map(session)
        self._build_commit_map(session)
        session.close()

    def build(self):
        session = self.Session(expire_on_commit=False)
        start_time = datetime.datetime.now()
        self._add_canonical_authors(session)
        head = self.repository.head.commit
        if self.shas_to_commits.get(head.hexsha):
            _print_line_counts(self.shas_to_commits[head.hexsha].line_counts)
            return
        self._add_commit_object(head, session)
        head_line_counts = self._make_full_commit_stats(head)
        self._add_commit_line_counts(head, head_line_counts, session)
        commits_to_process = deque([head])
        commit_count = 1
        print('Commit {:>5}: {}'.format(
            commit_count, datetime.datetime.now() - start_time))
        while commits_to_process:
            current_commit = commits_to_process.popleft()
            current_commit_stats = self.shas_to_commits[current_commit.hexsha].line_counts
            for parent in current_commit.parents:
                if not self.shas_to_commits.get(parent.hexsha):
                    self._add_commit_object(parent, session)
                    parent_line_counts = self._make_diffed_commit_stats(
                        parent, current_commit, current_commit_stats)
                    self._add_commit_line_counts(
                        parent, parent_line_counts, session)
                    commits_to_process.append(parent)
                    commit_count += 1
                    if commit_count % 20 == 0:
                        print('Commit {:>5}: {}'.format(
                            commit_count, datetime.datetime.now() - start_time))
                self.shas_to_commits[current_commit.hexsha].parent_ids.append(parent.hexsha)
        session.commit()
        _print_line_counts(self.shas_to_commits[head.hexsha].line_counts)

    def _iter_branch(self, branch_name=None):
        commits = []
        branch = self.repository.branches[branch_name] if branch_name else self.repository.head
        commit_id = branch.commit.hexsha
        while commit_id:
            commit = self.shas_to_commits.get(commit_id)
            if commit:
                commits.append(commit)
                commit_id = commit.parent_ids[0] if commit.parent_ids else None
            else:
                break
        return reversed(commits).__iter__()

    def iter_authors(self):
        return set(self.names_to_authors.values()).__iter__()

    def iter_commits(self, **kwargs):
        branch_iterator = self._iter_branch(kwargs.get('branch_name'))
        if not kwargs.get('frequency'):
            for commit in branch_iterator:
                yield commit
        else:
            next_commit_time = None
            for commit in branch_iterator:
                if not next_commit_time or commit.commit_time >= next_commit_time:
                    yield commit
                    start = _start_of_interval(commit.commit_time, kwargs['frequency'])
                    next_commit_time = kwargs['frequency'].next_instance(start)
