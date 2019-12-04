import os
import tempfile
import unittest

from githammer import Hammer


class HammerTest(unittest.TestCase):

    _main_repo_initial_commit_hexsha = 'c153f2881f0f0025a9ff5754e74111333ce859cd'

    def _fetch_commit(self, hexsha, hammer=None):
        if hammer is None:
            hammer = self.hammer
        return next(c for c in hammer.iter_individual_commits() if c.hexsha == hexsha)

    def _make_hammer(self, project_name):
        return Hammer(project_name, self.database_url)

    def setUp(self):
        self.current_directory = os.path.abspath(os.path.dirname(__file__))
        self.working_directory = tempfile.TemporaryDirectory(prefix='git-hammer-')
        self.database_url = 'sqlite:///' + self.working_directory.name + '/test.sqlite'
        self.hammer = self._make_hammer('test')

    def tearDown(self):
        self.working_directory.cleanup()
