import argparse

from .graph import *
from .hammer import Hammer


def init_project(options):
    hammer = Hammer(options.project)
    if options.repository:
        hammer.add_repository(options.repository, options.configuration)
        hammer.update_data()


def update_project(options):
    hammer = Hammer(options.project)
    hammer.update_data()


def add_repository(options):
    hammer = Hammer(options.project)
    hammer.add_repository(options.repository, options.configuration)
    hammer.update_data()


def plot_graph(options):
    hammer = Hammer(options.project)
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


parser = argparse.ArgumentParser(prog='githammer',
                                 description='Extract statistics from Git repositories')
command_parsers = parser.add_subparsers()

init_parser = command_parsers.add_parser('init-project', help='Initialize a new project')
init_parser.add_argument('project', help='Name of the project to create')
init_parser.add_argument('-r', '--repository', help='Git repository to create the project from')
init_parser.add_argument('-c', '--configuration', help='Path to the repository configuration file')
init_parser.set_defaults(func=init_project)

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

parsed_args = parser.parse_args()
parsed_args.func(parsed_args)
