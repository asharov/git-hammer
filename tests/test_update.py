import os
import git

from .hammer_test import HammerTest


class HammerUpdateTest(HammerTest):

    def _update_from_old_state(self):
        self.git_repository.remote().fetch('+refs/heads/master:refs/remotes/origin/master')
        self.git_repository.create_head('master', self.git_repository.remote().refs.master)
        self.git_repository.heads.master.checkout()
        self.hammer.update_data()

    def setUp(self):
        super().setUp()
        self.git_repository = git.Repo.clone_from(os.path.join(self.current_directory, 'data', 'repository'),
                                                  os.path.join(self.working_directory.name, 'worktree'),
                                                  branch='old-state', single_branch=True)
        self.hammer.add_repository(os.path.join(self.working_directory.name, 'worktree'))

    def test_clone_produced_expected_result(self):
        commits = list(self.hammer.iter_individual_commits())
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0].hexsha, HammerUpdateTest._main_repo_initial_commit_hexsha)

    def test_correct_statistics_were_computed_for_old_state(self):
        line_counts = self.hammer.head_commit().line_counts
        self.assertEqual(len(line_counts), 1)
        initial_commit = self._fetch_commit(HammerUpdateTest._main_repo_initial_commit_hexsha)
        self.assertIn(initial_commit.author, line_counts)
        self.assertEqual(line_counts[initial_commit.author], 14)

    def test_update_after_repository_updated_brings_in_new_commits(self):
        self._update_from_old_state()
        commits = list(self.hammer.iter_individual_commits())
        self.assertGreaterEqual(len(commits), 2)
        self.assertEqual(commits[0].hexsha, HammerUpdateTest._main_repo_initial_commit_hexsha)
        self.assertEqual(commits[1].hexsha, HammerUpdateTest._main_repo_second_commit_hexsha)

    def test_update_after_repository_updated_computes_correct_statistics(self):
        self._update_from_old_state()
        initial_commit = self._fetch_commit(HammerUpdateTest._main_repo_initial_commit_hexsha)
        second_commit = self._fetch_commit(HammerUpdateTest._main_repo_second_commit_hexsha)
        self.assertEqual(second_commit.line_counts[initial_commit.author], 10)
        self.assertEqual(second_commit.line_counts[second_commit.author], 4)
