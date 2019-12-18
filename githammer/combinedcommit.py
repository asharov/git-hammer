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

from operator import attrgetter

from .countdict import add_count_dict


def _iter_combined_commits(iterators):
    current_values = [None] * len(iterators)
    has_finished = [False] * len(iterators)
    next_values = [None] * len(iterators)
    for index, iterator in enumerate(iterators):
        try:
            next_values[index] = next(iterator)
        except StopIteration:
            has_finished[index] = True
    while not all(has_finished):
        min_index = None
        earliest_time = None
        for index, commit in enumerate(next_values):
            if not commit or has_finished[index]:
                continue
            if not earliest_time or commit.commit_time < earliest_time:
                min_index = index
                earliest_time = commit.commit_time
        if min_index is not None:
            current_values[min_index] = next_values[min_index]
            yield CombinedCommit(current_values)
            try:
                next_values[min_index] = next(iterators[min_index])
            except StopIteration:
                has_finished[min_index] = True
        else:
            return


class CombinedCommit:

    def __init__(self, commits):
        actual_commits = [commit for commit in commits if commit is not None]
        max_index, max_commit = max(enumerate(actual_commits), key=lambda pair: pair[1].commit_time)
        self.commit_time = max_commit.commit_time
        self.commit_time_utc_offset = actual_commits[max_index].commit_time_utc_offset
        self.line_counts = {}
        self.test_counts = {}
        for commit in commits:
            if commit is not None:
                self.line_counts = add_count_dict(self.line_counts, commit.line_counts)
                self.test_counts = add_count_dict(self.test_counts, commit.test_counts)
