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

    def test_repository_with_submodule_is_understood(self):
        self.hammer.add_repository(os.path.join(self.working_directory.name, 'worktree'))
        self.assertIsNotNone(self.hammer.head_commit())
