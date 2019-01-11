import argparse

from .graph import lines_per_author
from .hammer import Hammer

parser = argparse.ArgumentParser(
    description='Extract statistics from Git repositories')
parser.add_argument('repository')
parser.add_argument('--project')
parser.add_argument('--configuration')
options = parser.parse_args()
hammer = Hammer(options.repository, options.project, options.configuration)
hammer.build()
lines_per_author(hammer)
