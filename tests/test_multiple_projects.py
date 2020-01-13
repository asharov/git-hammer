import os

from githammer import iter_all_project_names

from .hammer_test import HammerTest


class HammerMultipleProjectsTest(HammerTest):

    _other_repo_initial_commit_hexsha = 'f0e9a62c80e7ffc3f2906da0f4c25aaf0b5a35a9'

    def _create_second_project(self):
        self.otherHammer = self._make_hammer('otherTest')
        self.otherHammer.add_repository(os.path.join(self.current_directory, 'data', 'subrepository'))

    def setUp(self):
        super().setUp()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'))

    def test_second_project_is_created(self):
        self._create_second_project()
        self.assertEqual(self.otherHammer.project_name, 'otherTest')

    def test_projects_are_inserted_in_database(self):
        self._create_second_project()
        project_names = list(iter_all_project_names(self.database_url))
        self.assertEqual(sorted(project_names), ['otherTest', 'test'])

    def test_commits_from_other_projects_are_not_included(self):
        self._create_second_project()
        with self.assertRaises(StopIteration):
            self._fetch_commit(HammerMultipleProjectsTest._main_repo_initial_commit_hexsha, hammer=self.otherHammer)

    def test_authors_from_other_projects_are_not_included(self):
        self._create_second_project()
        authors = list(self.otherHammer.iter_authors())
        self.assertEqual(len(authors), 1)

    def test_one_repository_can_be_added_to_multiple_projects(self):
        self._create_second_project()
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'other-repository'))
        self.otherHammer.add_repository(os.path.join(self.current_directory, 'data', 'other-repository'))
        self.assertIsNotNone(self._fetch_commit(HammerMultipleProjectsTest._other_repo_initial_commit_hexsha))
        self.assertIsNotNone(
            self._fetch_commit(HammerMultipleProjectsTest._other_repo_initial_commit_hexsha, hammer=self.otherHammer))
