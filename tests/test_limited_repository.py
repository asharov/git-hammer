import os
import datetime

import git

from .hammer_test import HammerTest


class HammerLimitedTest(HammerTest):
    def setUp(self):
        super().setUp()
        self.start_date = datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        self.hammer.add_repository(os.path.join(self.current_directory, 'data', 'repository'),
                                   os.path.join(self.current_directory, 'data', 'repo-config.json'),
                                   earliest_date=self.start_date)

    def test_limiting_by_date_includes_only_commits_after(self):
        commits = list(self.hammer.iter_individual_commits())
        self.assertEqual(len(commits), 3)

    def test_line_counts_are_correct_in_date_limited_repository(self):
        authors = {author.name: author for author in self.hammer.iter_authors()}
        self.assertEqual(self.hammer.head_commit().line_counts, {
            authors['Author A']: 7,
            authors['Author B']: 9,
            authors['Author C']: 2
        })

    def test_updating_project_does_not_add_new_commits(self):
        self.hammer.update_data()
        commits = list(self.hammer.iter_individual_commits())
        self.assertEqual(len(commits), 3)

    def test_updating_brings_in_later_commits_but_not_excluded_ones(self):
        other_hammer = self._make_hammer('otherTest',
                                         database_url='sqlite:///' + self.working_directory.name + '/other.sqlite')
        git_repository = git.Repo.clone_from(os.path.join(self.current_directory, 'data', 'repository'),
                                             os.path.join(self.working_directory.name, 'worktree'),
                                             branch='december', single_branch=True)
        other_hammer.add_repository(os.path.join(self.working_directory.name, 'worktree'),
                                    earliest_date=self.start_date)
        initial_commits = list(other_hammer.iter_individual_commits())
        self.assertEqual(len(initial_commits), 1)
        git_repository.remote().fetch('+refs/heads/master:refs/remotes/origin/master')
        git_repository.create_head('master', git_repository.remote().refs.master)
        git_repository.heads.master.checkout()
        other_hammer.update_data()
        updated_commits = list(other_hammer.iter_individual_commits())
        self.assertEqual(len(updated_commits), 3)
