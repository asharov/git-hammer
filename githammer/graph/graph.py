import matplotlib

matplotlib.use('TkAgg')
import matplotlib.dates as mpdates
import matplotlib.pyplot as mpplot

from githammer import Frequency

from operator import attrgetter


class NoDataForGraphError(Exception):
    pass


def total_lines(hammer):
    date_array = []
    line_count_array = []
    for commit in hammer.iter_commits(frequency=Frequency.daily):
        date_array.append(commit.commit_time)
        line_count_array.append(sum(commit.line_counts.values()))
    date_plot_array = mpdates.date2num(date_array)
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.plot_date(date_plot_array, line_count_array, ls='-', marker='')
    figure.autofmt_xdate(rotation=45)
    figure.tight_layout()
    mpplot.show()


def lines_per_author(hammer, min_lines_per_author=0):
    selected_authors = set()
    for commit in hammer.iter_commits():
        for author, line_count in commit.line_counts.items():
            if line_count >= min_lines_per_author:
                selected_authors.add(author)
    if not selected_authors:
        raise NoDataForGraphError(
            'No authors were found having at least {} lines in a single commit'.format(min_lines_per_author))
    author_list = sorted(list(selected_authors), key=attrgetter('name'))
    author_labels = [author.name for author in author_list]
    date_array = []
    line_count_array = [[] for _ in range(len(author_list))]
    for commit in hammer.iter_commits(frequency=Frequency.daily):
        date_array.append(commit.commit_time)
        for index, author in enumerate(author_list):
            line_count_array[index].append(commit.line_counts.get(author, 0))
    figure = mpplot.figure()
    plot = figure.add_subplot(111)
    plot.stackplot(date_array, line_count_array, labels=author_labels)
    figure.autofmt_xdate(rotation=45)
    figure.legend(loc='upper left')
    figure.tight_layout()
    mpplot.show()
