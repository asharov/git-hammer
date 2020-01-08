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

import argparse
import datetime
import os
import sys
import matplotlib.pyplot as plt

from dateutil.parser import parse

from .hammer import Hammer, iter_all_project_names, iter_sources_and_tests
from .summary import *


def make_hammer(project):
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return Hammer(project, database_url=database_url)
    else:
        return Hammer(project)


def update_project(options):
    hammer = make_hammer(options.project)
    hammer.update_data()


def add_repository(options):
    hammer = make_hammer(options.project)
    if options.earliest_commit_date:
        date = parse(options.earliest_commit_date)
        if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
            date = date.replace(tzinfo=datetime.timezone.utc)
        hammer.add_repository(options.repository, options.configuration, earliest_date=date)
    else:
        hammer.add_repository(options.repository, options.configuration)


def list_projects(_):
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        iterator = iter_all_project_names(database_url=database_url)
    else:
        iterator = iter_all_project_names()
    for name in iterator:
        print(name)


def list_sources(options):
    for item_type, item in iter_sources_and_tests(options.repository, options.configuration):
        if item_type == 'source-file':
            print('S: {}'.format(item))
        elif item_type == 'test-file':
            print('T: {}'.format(item))
        elif item_type == 'test-line':
            print('|---{}'.format(item))


def plot_graph(options):
    hammer = make_hammer(options.project)
    figure = None
    if options.type == 'line-count':
        figure = total_lines(hammer)
    elif options.type == 'line-author-count':
        figure = lines_per_author(hammer)
    elif options.type == 'test-count':
        figure = total_tests(hammer)
    elif options.type == 'test-author-count':
        figure = tests_per_author(hammer)
    elif options.type == 'day-of-week':
        figure = commits_per_weekday(hammer)
    elif options.type == 'time-of-day':
        figure = commits_per_hour(hammer)
    if figure:
        if options.output_file:
            figure.savefig(options.output_file)
        else:
            plt.show()


def print_summary(options):
    hammer = make_hammer(options.project)
    handle = open(options.output_file, 'w') if options.output_file else sys.stdout
    handle.write(str(commit_count_table(hammer)))
    handle.write('\n\n')
    handle.write(str(line_count_table(hammer)))
    test_counts = test_count_table(hammer)
    if test_counts:
        handle.write('\n\n')
        handle.write(str(test_counts))
    handle.write('\n')
    if handle is not sys.stdout:
        handle.close()


parser = argparse.ArgumentParser(prog='githammer',
                                 description='Extract statistics from Git repositories')
command_parsers = parser.add_subparsers()

init_parser = command_parsers.add_parser('init-project', help='Initialize a new project')
init_parser.add_argument('project', help='Name of the project to create')
init_parser.add_argument('repository', help='Git repository to create the project from')
init_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
init_parser.add_argument('--earliest-commit-date', help='Ignore commits prior to this date')
init_parser.set_defaults(func=add_repository)

update_parser = command_parsers.add_parser('update-project', help='Update an existing project with new commits')
update_parser.add_argument('project', help='Name of the project to update')
update_parser.set_defaults(func=update_project)

add_parser = command_parsers.add_parser('add-repository', help='Add a repository to an existing project')
add_parser.add_argument('project', help='Project to add the repository to')
add_parser.add_argument('repository', help='Path to the git repository to add')
add_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
add_parser.add_argument('--earliest-commit-date', help='Ignore commits prior to this date')
add_parser.set_defaults(func=add_repository)

project_list_parser = command_parsers.add_parser('list-projects', help='List names of existing projects')
project_list_parser.set_defaults(func=list_projects)

source_list_parser = command_parsers.add_parser('list-sources', help='List source files and test lines in repository')
source_list_parser.add_argument('repository', help='Git repository to examine')
source_list_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
source_list_parser.set_defaults(func=list_sources)

graph_parser = command_parsers.add_parser('graph', help='Draw line count per committer graph')
graph_parser.add_argument('project', help='Name of the project to graph')
graph_parser.add_argument('type', help='The type of graph to make',
                          choices=['line-count', 'line-author-count', 'test-count', 'test-author-count', 'day-of-week',
                                   'time-of-day'])
graph_parser.add_argument('-o', '--output-file',
                          help='Name of the file to save the graph to. If omitted, graph is displayed on screen')
graph_parser.set_defaults(func=plot_graph)

summary_parser = command_parsers.add_parser('summary',
                                            help='Print summary information of the current state of the project')
summary_parser.add_argument('project', help='Name of the project to summarize')
summary_parser.add_argument('-o', '--output-file',
                            help='Name of the file to print the summary to. If omitted, summary is printed to standard output')
summary_parser.set_defaults(func=print_summary)

parsed_args = parser.parse_args()
parsed_args.func(parsed_args)
