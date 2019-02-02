import os
import tempfile
import unittest

from githammer import Hammer


class HammerTest(unittest.TestCase):

    def setUp(self):
        self.current_directory = os.path.abspath(os.path.dirname(__file__))
        self.working_directory = tempfile.TemporaryDirectory(prefix='git-hammer-')
        self.server_url = 'sqlite:///' + self.working_directory.name + '/'
        self.hammer = Hammer('test', self.server_url)

    def tearDown(self):
        self.working_directory.cleanup()
