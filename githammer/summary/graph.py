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

import matplotlib.pyplot as mpplot

from githammer import Frequency


class NoDataForGraphError(Exception):
    pass


def _plot_totals(hammer, counts_property):
    date_array = []
    line_count_array = []
    for commit in hammer.iter_commits(frequency=Frequency.daily):
        date_array.append(commit.commit_time)
        line_count_array.append(sum(getattr(commit, counts_property).values()))
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.plot(date_array, line_count_array, ls='-', marker='')
    figure.autofmt_xdate(rotation=45)
    figure.tight_layout()
    return figure


def _plot_totals_per_author(hammer, counts_property, min_count_per_author=0):
    selected_authors = set()
    for commit in hammer.iter_commits():
        for author, count in getattr(commit, counts_property).items():
            if count >= min_count_per_author:
                selected_authors.add(author)
    if not selected_authors:
        raise NoDataForGraphError(
            'No authors were found having at least a count of {} in a single commit'.format(min_count_per_author))
    author_list = sorted(list(selected_authors), key=attrgetter('name'))
    author_labels = [author.name for author in author_list]
    date_array = []
    count_array = [[] for _ in range(len(author_list))]
    for commit in hammer.iter_commits(frequency=Frequency.daily):
        date_array.append(commit.commit_time)
        for index, author in enumerate(author_list):
            count_array[index].append(getattr(commit, counts_property).get(author, 0))
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.stackplot(date_array, count_array, labels=author_labels)
    figure.autofmt_xdate(rotation=45)
    figure.legend(loc='upper left')
    figure.tight_layout()
    return figure


def total_lines(hammer):
    return _plot_totals(hammer, 'line_counts')


def total_tests(hammer):
    return _plot_totals(hammer, 'test_counts')


def lines_per_author(hammer):
    return _plot_totals_per_author(hammer, 'line_counts')


def tests_per_author(hammer):
    return _plot_totals_per_author(hammer, 'test_counts')


def commits_per_hour(hammer):
    count_array = [0] * 24
    for commit in hammer.iter_individual_commits():
        count_array[commit.commit_time_tz().hour] += 1
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.bar(range(len(count_array)), count_array)
    figure.tight_layout()
    return figure


def commits_per_weekday(hammer):
    count_array = [0] * 7
    for commit in hammer.iter_individual_commits():
        count_array[commit.commit_time_tz().weekday()] += 1
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.bar(range(len(count_array)), count_array)
    figure.tight_layout()
    mpplot.xticks(range(len(count_array)),
                  ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
    return figure
