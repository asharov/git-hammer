import re

_glob_replacements = {
    '/**/': '/.*/?',
    '/**': '/.*',
    '**/': '.*/',
    '*': '[^/]*',
    '?': '.'
}
_glob_patterns = sorted(_glob_replacements, key=len, reverse=True)
_glob_pattern_matcher = re.compile('|'.join(map(re.escape, _glob_patterns)))


def _glob_to_regex(glob):
    regex = _glob_pattern_matcher.sub(
        lambda match: _glob_replacements[match.group(0)], glob)
    return regex + '$'


def matches_glob(glob, string):
    regex = _glob_to_regex(glob)
    return re.search(regex, string) is not None
