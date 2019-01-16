import argparse

from .graph import lines_per_author
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


def plot_line_counts_per_author(options):
    hammer = Hammer(options.project)
    lines_per_author(hammer)


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
graph_parser.set_defaults(func=plot_line_counts_per_author)

parsed_args = parser.parse_args()
parsed_args.func(parsed_args)
