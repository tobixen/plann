# Changelog

The format of this file is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), 
and I do try to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.1.0] - [unreleased]

### Added

* Added possibility to add calendar name and calendar url to the template.  Ref https://github.com/tobixen/plann/issues/14 by @rjolina at github.
* `now` should be an acceptable timestamp.  Ref https://github.com/tobixen/plann/issues/16

### Changed

* Various documentation improvements, some of it by @WhyNotHugo at github in https://github.com/tobixen/plann/pull/15

### Fixed

* `--help` had some wrong information, ref https://github.com/tobixen/plann/issues/16 by Thomas Maeder

## [v1.0.0] - 2024-12-01

Changelogs up until 1.0 has been dropped, as development was going
rather fast-paced and erratic, with the priority of getting a tool the
author can use for his daily planning.  Very little development was
done in 2024, but the tool works for me.

The 1.0.0-version probably has plenty of rough edges as it hasn't been
tested much and is lacking some test code, but if nothing else I will
try to stick to better development practices from now on - not
breaking backward compatibility unless I really have to (and then
under a 2.0-release), fewer commits with sane commit messages towards
the main branch, silly commits going to side branches, keep the
changelog up-to-date, make sure new features are sufficiently covered
by test-code, etc.
