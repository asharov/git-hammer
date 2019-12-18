import re
import errno
import json

from globber import globber


def _matches_file_pattern(file, pattern):
    if type(pattern) is str:
        return globber.match(pattern, file)
    elif type(pattern) is list:
        return any(_matches_file_pattern(file, p) for p in pattern)
    else:
        raise TypeError('Pattern {} not list or string'.format(pattern))


class Configuration:
    def __init__(self, file_path=None):
        if file_path:
            try:
                fp = open(file_path, 'r')
            except OSError as error:
                if error.errno == errno.ENOENT:
                    config_json = {}
                else:
                    raise error
            else:
                try:
                    config_json = json.load(fp)
                finally:
                    fp.close()
        else:
            config_json = {}
        if 'sourceFiles' in config_json:
            self.source_files = config_json['sourceFiles']
        else:
            self.source_files = None
        if 'excludedSourceFiles' in config_json:
            self.excluded_source_files = config_json['excludedSourceFiles']
        else:
            self.excluded_source_files = None
        if 'testFiles' in config_json:
            self.test_files = config_json['testFiles']
        else:
            self.test_files = None
        if 'testLineRegex' in config_json:
            self.test_line_regex = re.compile(config_json['testLineRegex'])
        else:
            self.test_line_regex = None

    def is_source_file(self, path):
        is_included = self.source_files is None or _matches_file_pattern(path, self.source_files)
        is_excluded = self.excluded_source_files is not None and _matches_file_pattern(path, self.excluded_source_files)
        return is_included and not is_excluded

    def is_test_file(self, path):
        if not self.is_source_file(path):
            return False
        return self.test_files is not None and _matches_file_pattern(path, self.test_files)

    def iter_test_lines(self, path, lines):
        if not self.is_test_file(path):
            return
        for line in lines:
            if self.test_line_regex.search(line):
                yield line
