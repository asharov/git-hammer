import os
import tempfile
import unittest

from githammer import Hammer


class HammerTest(unittest.TestCase):

    _main_repo_initial_commit_hexsha = 'c153f2881f0f0025a9ff5754e74111333ce859cd'
    _main_repo_second_commit_hexsha = '5151985f7e3551c73ccb65cda2b021194b30b30a'
    _main_repo_head_commit_hexsha = '9f5ed1b1c43e211a30e6b9cc60ce26540ab9df70'

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
