import sys
import itertools

from githammer import Hammer


def check_commit(index, commit_old, commit_new, attr):
    old_attr = getattr(commit_old, attr)
    new_attr = getattr(commit_new, attr)
    if old_attr != new_attr:
        sys.exit('Error in commit {} ({}): Incorrect {} {} (expected {})'.
                 format(index, commit_old.hexsha, attr, new_attr, old_attr))


if len(sys.argv) < 3:
    sys.exit('Usage: {} <known good project> <new project>'.format(sys.argv[0]))

hammer_old = Hammer(sys.argv[1])
hammer_new = Hammer(sys.argv[2])

count = 0

for (index, (commit_old, commit_new)) in enumerate(itertools.zip_longest(hammer_old.iter_individual_commits(),
                                                                         hammer_new.iter_individual_commits())):
    check_commit(index, commit_old, commit_new, 'hexsha')
    check_commit(index, commit_old, commit_new, 'author_name')
    check_commit(index, commit_old, commit_new, 'added_lines')
    check_commit(index, commit_old, commit_new, 'deleted_lines')
    check_commit(index, commit_old, commit_new, 'commit_time')
    check_commit(index, commit_old, commit_new, 'commit_time_utc_offset')
    check_commit(index, commit_old, commit_new, 'line_counts')
    check_commit(index, commit_old, commit_new, 'test_counts')
    count += 1

print('OK, checked {} commits'.format(count))
