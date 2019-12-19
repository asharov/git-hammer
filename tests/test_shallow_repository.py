import os
import git

from .hammer_test import HammerTest


class HammerShallowTest(HammerTest):
    def setUp(self):
        super().setUp()
        self.git_repository = git.Repo.clone_from('file://' + os.path.join(self.current_directory, 'data', 'repository'),
                                                  os.path.join(self.working_directory.name, 'worktree'),
                                                  depth=1)
        self.hammer.add_repository(os.path.join(self.working_directory.name, 'worktree'),
                                   os.path.join(self.current_directory, 'data', 'repo-config.json'))

    def test_shallow_clone_has_only_one_commit(self):
        commits = list(self.hammer.iter_individual_commits())
        self.assertEqual(len(commits), 1)

    def test_shallow_clone_has_correct_counts(self):
        commit = self._fetch_commit(HammerShallowTest._main_repo_head_commit_hexsha)
        line_counts = commit.line_counts.values()
        self.assertEqual(sorted(line_counts), [18])
