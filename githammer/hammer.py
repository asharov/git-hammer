import argparse
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

from .countdict import add_count_dict, subtract_count_dict
from .dbtypes import Author, Base, Commit, LineCount

_glob_replacements = {
    '/**/': '/.*/',
    '/**': '/.*',
    '**/': '.*/',
    '*': '[^/]*',
    '?': '.'
}
_glob_patterns = sorted(_glob_replacements, key=len, reverse=True)
_glob_pattern_matcher = re.compile('|'.join(map(re.escape, _glob_patterns)))

_diff_stat_regex = re.compile('^([0-9]+|-)\t([0-9]+|-)\t(.*)$')


def _glob_to_regex(glob):
    regex = _glob_pattern_matcher.sub(
        lambda match: _glob_replacements[match.group(0)], glob)
    return regex + '$'


def _matches_file_pattern(file, pattern):
    if type(pattern) is str:
        regex = _glob_to_regex(pattern)
        return re.search(regex, file) != None
    elif type(pattern) is list:
        return any(_matches_file_pattern(file, p) for p in pattern)
    else:
        raise TypeError('Pattern {} not list or string'.format(pattern))


def _print_line_counts(linecounts):
    for author, count in sorted(linecounts.items(), key=itemgetter(1), reverse=True):
        print('{}\t{}'.format(count, author.canonical_name))


def _author_line(commit):
    return f"{commit.author.name} <{commit.author.email}>"


class Hammer:

    def _build_author_map(self):
        authors = {}
        session = self.Session()
        for dbauthor in session.query(Author):
            authors[dbauthor.canonical_name] = dbauthor
            for alias in dbauthor.aliases:
                authors[alias] = dbauthor
        session.close()
        return authors

    def _is_source_file(self, path):
        source_files = self.configuration.get('sourceFiles')
        excluded_source_files = self.configuration.get('excludedSourceFiles')
        is_included = source_files == None or _matches_file_pattern(
            path, source_files)
        is_excluded = excluded_source_files != None and _matches_file_pattern(
            path, excluded_source_files)
        return is_included and not is_excluded

    def _blame_blob_into_linecounts(self, commit_to_blame, path, linecounts):
        if not self._is_source_file(path):
            return
        blame = self.repository.blame(commit_to_blame, path, w=True)
        for commit, lines in blame:
            author = self.names_to_authors[_author_line(commit)]
            linecounts[author] = linecounts.get(author, 0) + len(lines)

    def _make_full_commit_stats(self, commit):
        linecounts = {}
        for object in commit.tree.traverse(visit_once=True):
            if object.type != 'blob':
                continue
            self._blame_blob_into_linecounts(
                commit, object.path, linecounts)
        return linecounts

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
        next_linecounts = {}
        current_linecounts = {}
        for current_file in current_files:
            self._blame_blob_into_linecounts(
                current_commit, current_file, current_linecounts)
        for next_file in next_files:
            self._blame_blob_into_linecounts(
                next_commit, next_file, next_linecounts)
        difference = subtract_count_dict(current_linecounts, next_linecounts)
        linecounts = add_count_dict(next_commit_stats, difference)
        return linecounts

    def _add_author_alias_if_needed(self, author_line):
        if not self.names_to_authors.get(author_line):
            canonical_name = self.repository.git.check_mailmap(author_line)
            author = self.names_to_authors.get(canonical_name)
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
        author_line = _author_line(commit)
        self._add_author_alias_if_needed(author_line)
        author = self.names_to_authors[author_line]
        commit_object = Commit(
            hexsha=commit.hexsha, author=author, commit_time=commit.authored_datetime)
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
        session.add(commit_object)

    def _add_commit_linecounts(self, commit, linecounts, session):
        for author, count in linecounts.items():
            linecount = LineCount(
                author_name=author.canonical_name, commit_id=commit.hexsha, line_count=count)
            session.add(linecount)

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
        self.names_to_authors = self._build_author_map()

    def build(self):
        session = self.Session(expire_on_commit=False)
        start_time = datetime.datetime.now()
        self._add_canonical_authors(session)
        processed_commits = {}
        head = self.repository.head.commit
        self._add_commit_object(head, session)
        head_linecounts = self._make_full_commit_stats(head)
        self._add_commit_linecounts(head, head_linecounts, session)
        processed_commits[head.hexsha] = head_linecounts
        commits_to_process = deque([head])
        commit_count = 1
        print('Commit {:>5}: {}'.format(
            commit_count, datetime.datetime.now() - start_time))
        while commits_to_process:
            current_commit = commits_to_process.popleft()
            current_commit_stats = processed_commits[current_commit.hexsha]
            for parent in current_commit.parents:
                if not processed_commits.get(parent.hexsha):
                    self._add_commit_object(parent, session)
                    parent_linecounts = self._make_diffed_commit_stats(
                        parent, current_commit, current_commit_stats)
                    self._add_commit_linecounts(
                        parent, parent_linecounts, session)
                    processed_commits[parent.hexsha] = parent_linecounts
                    commits_to_process.append(parent)
                    commit_count += 1
                    if commit_count % 20 == 0:
                        print('Commit {:>5}: {}'.format(
                            commit_count, datetime.datetime.now() - start_time))
        session.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract statistics from Git repositories')
    parser.add_argument('repository')
    parser.add_argument('--project')
    parser.add_argument('--configuration')
    options = parser.parse_args()
    hammer = Hammer(options.repository, options.project, options.configuration)
    hammer.build()
