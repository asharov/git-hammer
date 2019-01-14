from operator import attrgetter

from .countdict import add_count_dict


def _iter_combined_commits(iterators):
    current_values = [None] * len(iterators)
    has_finished = [False] * len(iterators)
    next_values = [None] * len(iterators)
    for index, iterator in enumerate(iterators):
        try:
            next_values[index] = next(iterator)
        except StopIteration:
            has_finished[index] = True
    while not all(has_finished):
        min_index = None
        earliest_time = None
        for index, commit in enumerate(next_values):
            if not commit or has_finished[index]:
                continue
            if not earliest_time or commit.commit_time < earliest_time:
                min_index = index
                earliest_time = commit.commit_time
        if min_index is not None:
            current_values[min_index] = next_values[min_index]
            yield CombinedCommit(current_values)
            try:
                next_values[min_index] = next(iterators[min_index])
            except StopIteration:
                has_finished[min_index] = True
        else:
            return


class CombinedCommit:

    def __init__(self, commits):
        actual_commits = [commit for commit in commits if commit is not None]
        self.commit_time = max(map(attrgetter('commit_time'), actual_commits))
        self.line_counts = {}
        for commit in commits:
            if commit is not None:
                self.line_counts = add_count_dict(self.line_counts, commit.line_counts)
