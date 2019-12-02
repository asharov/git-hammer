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

from beautifultable import BeautifulTable


def _make_table(columns):
    table = BeautifulTable()
    table.set_style(BeautifulTable.STYLE_COMPACT)
    table.column_headers = columns
    for column in columns:
        if column == 'Author':
            table.column_alignments[column] = BeautifulTable.ALIGN_LEFT
        else:
            table.column_alignments[column] = BeautifulTable.ALIGN_RIGHT
    return table


def commit_count_table(hammer):
    commit_counts = {}
    for commit in hammer.iter_individual_commits():
        commit_counts[commit.author] = commit_counts.get(commit.author, 0) + 1
    table = _make_table(['Author', 'Commits'])
    for author, commit_count in commit_counts.items():
        table.append_row([author.name, commit_count])
    table.sort('Commits', reverse=True)
    return table


def line_count_table(hammer):
    head_commit = hammer.head_commit()
    table = _make_table(['Author', 'Lines'])
    for author, line_count in head_commit.line_counts.items():
        table.append_row([author.name, line_count])
    table.sort('Lines', reverse=True)
    return table


def test_count_table(hammer):
    head_commit = hammer.head_commit()
    if head_commit.test_counts:
        table = _make_table(['Author', 'Tests'])
        for author, test_count in head_commit.test_counts.items():
            table.append_row([author.name, test_count])
        table.sort('Tests', reverse=True)
        return table
    return None
