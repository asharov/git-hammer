# Git Hammer

[![Build Status](https://travis-ci.com/asharov/git-hammer.svg?branch=master)](https://travis-ci.com/asharov/git-hammer)
[![codecov](https://codecov.io/gh/asharov/git-hammer/branch/master/graph/badge.svg)](https://codecov.io/gh/asharov/git-hammer)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

---
NOTE: If you have been using Git Hammer prior to December 4th,
2019, your database is obsolete, and unfortunately you will need
to rebuild it if you want to use the current version. This is
because a necessary change in the database schema could not be
automatically migrated from the old version. Git Hammer has
now been set up to support database migrations better, and this
situation hopefully won't happen again. My apologies for the
inconvenience.
---

Git Hammer is a statistics tool for projects in git repositories.
Its major feature is tracking the number of lines authored by
each person for every commit, but it currently includes some
other useful statistics as well, and the data that it collects
could be used in multiple new ways as well.

Git Hammer is under active maintenance. New features appear when
a need or desire for them exists. If Git Hammer lacks some
feature you would like, all kinds of contributions are welcome,
from simple feature suggestions to complete pull requests
implementing the feature.

## Setup

By default, Git Hammer stores the historical information from
the repository in an SQLite database file in the current
directory. If you wish to change this default, set the
`DATABASE_URL` environment variable to a database URL
according to the [SQLAlchemy engine documentation](https://docs.sqlalchemy.org/en/latest/core/engines.html).
This database will be created if it does not already exist.
Note that if you wish to use a database other than SQLite,
you may need to install the appropriate Python module to
connect to the database.

You will need Python 3, at least version 3.5. It is a good
idea to set up a virtual environment, like this (run this
wherever you have cloned Git Hammer):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
The rest of the commands below assume that this has been done.

## Creating a Project

Now pick some git repository to run Git Hammer on. The examples
below use a hypothetical project called "baffle". You should
replace the name with your own.

```bash
python -m githammer init-project baffle ~/projects/baffle
```
This will create the database containing the project baffle
from the repository directory (here `~/projects/baffle`;
replace that with the path to your repository). Git Hammer
will print out a progress report while it goes through all
the commits in the repository.

(Incidentally, you should make sure that the main development
branch is the one checked out in the repository. Currently,
using Git Hammer really doesn't make sense otherwise.)

When the repository gets new development, first update the
code in the repository to the latest version, and then run
```bash
python -m githammer update-project baffle
```
This will process all the new commits that were not yet seen
into the database.

## Showing Statistics

After the project has been initialized and the repository added,
you can show some information on it. First try out
```bash
python -m githammer summary baffle
```
This will print out three tables: The number of commits for
each person, the number of lines of code written by each
person in the head version, and the number of tests written
by each person in the head version. This last is only printed
if the repository configuration includes test recognition (see
below).

There are a few graphs that Git Hammer can display. To see the
types of supported graphs, enter
```bash
python -m githammer graph --help
```
The graphs are

Type | Description
-----|------------
line-count    | Number of lines in the project over time
line-author-count | Same as above, except split per author
test-count | Number of tests in the project over time
test-author-count | Same as above, except split per author
day-of-week | A histogram showing the number of commits for each day of the week
time-of-day | A histogram showing the number of commits for each hour of the day

## Configuring Sources and Tests

By default, Git Hammer assumes that every file in the repository
is a source file and that there are no tests. This can be
modified by creating a configuration file. The configuration
file is JSON having some predefined keys:
```json
{
  "sourceFiles": [
    "Sources/**/*.py",
    "Tests/**/*.py",
    ...
  ],
  "excludedSourceFiles": [
    "Sources/Contrib/**"
  ],
  "testFiles": [
    "Tests/**/*.py"
  ],
  "testLineRegex": "def test_"
}
```

Here, `sourceFiles` is a list of patterns that match the source
files. Any file not matching one of these patterns is not
considered by Git Hammer. If `sourceFiles` captures too many
files, for instance autogenerated sources, `excludedSourceFiles`
is a list of patterns that will not be considered source even
if they match some `sourceFiles` pattern.

To include test counts, `testFiles` needs to be specified. This
is again, a list of patterns matching files that contain tests
(it is up to you if you wish to define this to mean unit tests,
integration tests, UI tests, etc.). Git Hammer will look inside
each of the test files. Any line matching the Python regular
expression `testLineRegex` is counted as one test. So
`testLineRegex` should typically match whatever acts as the
header of a test. Here, it is the definition of a function
named starting with `test_`. Other projects, and especially
other languages, will have different conventions.

All the file name patterns above (`sourceFiles`,
`excludedSourceFiles`, `testFiles`) are glob patterns as
defined by the
[globber library](https://github.com/asharov/globber).

The configuration file can be given as an option to the
`init-project` command:
```bash
python -m githammer init-project baffle ~/projects/baffle --configuration ./baffle-config.json
```
If the `--configuration` option is not given, but the repository
contains a file named `git-hammer-config.json`, this file will
be read as the configuration. This way you can keep the Git
Hammer configuration for a repository in that repository.

Note: The configuration file path, as well as the repository
path, will be stored in the database, so they should not be
moved. If the configuration changes, data that was already
in the database will not be reprocessed with the new
configuration.

## Multi-Repository Projects

Sometimes, a team works on multiple repositories that all still
belong to the same project. For instance, a piece of functionality
may be better to split off into a library in an independent
repository. Git Hammer supports such projects by not limiting
the project data to a single repository.

To add another repository to an existing project, just use
`add-repository`:
```bash
python -m githammer add-repository baffle ~/projects/baffle-common
```
This will process the new repository, adding it to the project
database. After this, any summary information will include
data from all repositories of the project. Like `init-project`,
`add-repository` also accepts the `--configuration` option to
specify the configuration file for the new repository.

## License

Git Hammer is licensed under the Apache Software License,
version 2.0. See the LICENSE file for precise license terms
and conditions.
