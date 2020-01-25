import os
import git

from .hammer_test import HammerTest


class HammerSubmoduleTest(HammerTest):

    def setUp(self):
        super().setUp()
        git.Repo.clone_from(os.path.join(self.current_directory, 'data', 'repository'),
                            os.path.join(self.working_directory.name, 'worktree'))
        repository = git.Repo(os.path.join(self.working_directory.name, 'worktree'))
        git.Submodule.add(repository, 'subrepo', 'subrepo',
                          os.path.join(self.current_directory, 'data', 'subrepository'))
        author = git.Actor('Author A', 'a@example.com')
        repository.index.commit('Add subrepo', author=author)

    def test_repository_with_added_submodule_is_understood(self):
        self.hammer.add_repository(os.path.join(self.working_directory.name, 'worktree'))
        self.assertIsNotNone(self.hammer.head_commit())

    def test_submodule_in_initial_commit_is_understood(self):
        submodule_repository = git.Repo.init(os.path.join(self.working_directory.name, 'initial_submodule'))
        git.Submodule.add(submodule_repository, 'subrepo', 'subrepo',
                          os.path.join(self.current_directory, 'data', 'subrepository'))
        author = git.Actor('Author B', 'b@example.com')
        submodule_repository.index.commit('Initial commit', author=author)
        self.hammer.add_repository(os.path.join(self.working_directory.name, 'initial_submodule'))
        commit = next(self.hammer.iter_individual_commits())
        self.assertEqual(commit.line_counts, {commit.author: 3})
