# Changelog

The format of this file is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), 
and I do try to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* `caldav_pass_command` config key and `--caldav-pass-command` command line option, for reading the CalDAV password from an external command (`pass`, `gpg`, `secret-tool`, ...) rather than storing it in plaintext in the configuration file.

## [v1.1.1] - 2026-05-28

### Added

* Added possibility to add calendar name and calendar url to the template.  Ref https://github.com/pycalendar/plann/issues/14 by @rjolina at github.
* `now` should be an acceptable timestamp.  Ref https://github.com/pycalendar/plann/issues/16
* Natural language timestamps now supported via `dateparser` — "yesterday", "3 hours ago", "Friday", etc. are accepted wherever a timestamp is expected.
* VJOURNAL support: new `plann add journal` command and `--journal` filter flag on `select`.  Ref https://github.com/tobixen/plann/issues/29
* Makefile with `install`, `dev`, `test`, `lint`, and `clean` targets, plus shell tab completion install targets.
* `features` config key is now passed to the caldav library, enabling server-specific compatibility workarounds (e.g. `"features": "davical"`).

### Changed

* Various documentation improvements, some of it by @WhyNotHugo at github in https://github.com/pycalendar/plann/pull/15

### Fixed

* `--help` had some wrong information, ref https://github.com/pycalendar/plann/issues/16 by Thomas Maeder
* Importing a VCALENDAR file containing multiple events/tasks failed.
* `procrastinate 0s` (and other zero-delay variants) was not treated as a no-op due to a typo (`'9s'` instead of `'0s'`).
* Timezone was incorrectly applied to all-day dates (`datetime.date`), causing off-by-one errors.
* When selecting by UID, component type (`--event`/`--todo`) no longer needs to be specified, and completed tasks are no longer incorrectly filtered out.

## [v1.1.0] - 2026-05-28

Same as v1.1.1, except the publishing workflow was not working

## [v1.0.0] - 2024-12-01

Changelogs up until 1.0 has been dropped, as development was going
rather fast-paced and erratic, with the priority of getting a tool the
author can use for his daily planning.  Very little development was
done in 2024 and 2025, but the tool works for me.

The 1.0.0-version probably has plenty of rough edges as it hasn't been
tested much and is lacking some test code, but if nothing else I will
try to stick to better development practices from now on - not
breaking backward compatibility unless I really have to (and then
under a 2.0-release), fewer commits with sane commit messages towards
the main branch, silly commits going to side branches, keep the
changelog up-to-date, make sure new features are sufficiently covered
by test-code, etc.
