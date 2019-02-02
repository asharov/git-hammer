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
import os

from .hammer import Hammer
from .summary import *


def make_hammer(project):
    server_url = os.environ.get('DATABASE_SERVER_URL')
    if server_url:
        return Hammer(project, database_server_url=server_url)
    else:
        return Hammer(project)


def update_project(options):
    hammer = make_hammer(options.project)
    hammer.update_data()


def add_repository(options):
    hammer = make_hammer(options.project)
    hammer.add_repository(options.repository, options.configuration)
    hammer.update_data()


def plot_graph(options):
    hammer = make_hammer(options.project)
    if options.type == 'line-count':
        total_lines(hammer)
    elif options.type == 'line-author-count':
        lines_per_author(hammer)
    elif options.type == 'test-count':
        total_tests(hammer)
    elif options.type == 'test-author-count':
        tests_per_author(hammer)
    elif options.type == 'day-of-week':
        commits_per_weekday(hammer)
    elif options.type == 'time-of-day':
        commits_per_hour(hammer)


def print_summary(options):
    hammer = make_hammer(options.project)
    commit_count_table(hammer)
    print()
    line_count_table(hammer)
    print()
    test_count_table(hammer)


parser = argparse.ArgumentParser(prog='githammer',
                                 description='Extract statistics from Git repositories')
command_parsers = parser.add_subparsers()

init_parser = command_parsers.add_parser('init-project', help='Initialize a new project')
init_parser.add_argument('project', help='Name of the project to create')
init_parser.add_argument('repository', help='Git repository to create the project from')
init_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
init_parser.set_defaults(func=add_repository)

update_parser = command_parsers.add_parser('update-project', help='Update an existing project with new commits')
update_parser.add_argument('project', help='Name of the project to update')
update_parser.set_defaults(func=update_project)

add_parser = command_parsers.add_parser('add-repository', help='Add a repository to an existing project')
add_parser.add_argument('project', help='Project to add the repository to')
add_parser.add_argument('repository', help='Path to the git repository to add')
add_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
add_parser.set_defaults(func=add_repository)

graph_parser = command_parsers.add_parser('graph', help='Draw line count per committer graph')
graph_parser.add_argument('project', help='Name of the project to graph')
graph_parser.add_argument('type', help='The type of graph to make',
                          choices=['line-count', 'line-author-count', 'test-count', 'test-author-count', 'day-of-week',
                                   'time-of-day'])
graph_parser.set_defaults(func=plot_graph)

summary_parser = command_parsers.add_parser('summary',
                                            help='Print summary information of the current state of the project')
summary_parser.add_argument('project', help='Name of the project to summarize')
summary_parser.set_defaults(func=print_summary)

parsed_args = parser.parse_args()
parsed_args.func(parsed_args)
