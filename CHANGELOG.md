# Changelog

The format of this file is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), 
and I do try to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* `edit --add-categories`, `--add-resource` and `--add-resources` options (alongside the existing `--add-category`).  The plural forms (`--add-categories`/`--add-resources`) split the value on comma; the singular forms (`--add-category`/`--add-resource`) keep a comma literal - so you do not have to remember whether to use singular or plural.
* `select ... list --separator=...` to join the listed items with something other than a newline.  (Ported from the archived development branch.)
* The interactive edit prompt now advertises the `start` command (kicks off time tracking for the task) and re-prompts afterwards so a follow-up command can be given for the same task.  (Ported from the archived development branch.)
* `select --warn-on-missing-uid/--no-warn-on-missing-uid` (default: warn).  A `--uid` that matches nothing in any calendar now prints a warning naming the missing uid(s) to stderr, rather than being silently ignored.  `--abort-on-missing-uid` still takes precedence, and `--no-warn-on-missing-uid` restores the old fully-silent behaviour.  Ref https://github.com/tobixen/plann/issues/42
* `plann configure`: an interactive configuration mode (EXPERIMENTAL/under-tested) that prompts for connection parameters and writes them to the config file.  The underlying code existed but had been orphaned in the argparse→click migration; it is now wired up again, and the prompted keys match what the caldav library actually reads (so e.g. `ssl_verify_cert` is no longer written under a key that is silently ignored at connect time).

### Fixed

* `add ical` with several concatenated VCALENDAR objects no longer silently ignores them all when the data uses CRLF line endings (the RFC 5545 canonical form): the split is now done by the icalendar library instead of a hand-rolled LF-only string scan.
* Showing help for a subcommand (e.g. `plann select --help`) no longer connects to every configured calendar; calendar discovery is deferred until a command actually needs it.
* A config section carrying `features` but no `caldav_url` crashed with `KeyError: 'url'`.  The caldav library resolves the URL from the server profile given in `features`, so no URL is needed.  (This also requires a caldav release newer than 3.2.1 - with older caldav versions such a section is silently skipped instead of crashing.)
* The time tracking integration (`"extra_config": {"time_tracking": ["timewarrior"]}` in a config section) did not work: the configuration was attached to the calendar objects under a different attribute name than the time tracking code read, and only the value `timew` was accepted - not `timewarrior` as the error message suggested.  (Fixes ported from the archived development branch.)
* Exporting an event/task to timewarrior no longer removes the categories from the object.
* `select ... delete` now reports what it did: it names each item as it is deleted, and says "No items selected for deletion" on an empty selection instead of silently producing no output regardless of whether anything matched.  Ref https://github.com/tobixen/plann/issues/42

### Changed

* `edit --set-resources` now splits its value on comma, the same way `--set-categories` always has; `--set-resources a,b` now sets two resources rather than one resource literally named `a,b`.
* `edit --set-category` is now flagged as deprecated in its `--help`: it *appends* rather than replaces (the name does not convey this).  Use `--add-category` to append or `--set-categories` to replace.
* (internal) The `category`/`categories` (and now `resources`) handling on the edit path is driven by a single `COMMA_LIST_ATTRS` registry rather than being special-cased in several places.
* (internal) A template sort key (`--sort-key`) is now compiled once per key instead of being rebuilt on every comparison while sorting.
* (internal) A hierarchical `list --top-down`/`--bottom-up` now caches related tasks for the duration of the traversal instead of re-fetching the same task from the server once per relationship edge.
* (internal) `set-task-attribs` now fetches the task list once and filters client-side per attribute (via the `icalendar_searcher` library) instead of issuing a separate server query for each of category/due/priority/duration.  As a side effect, on calendar servers that do not filter properly it now finds tasks missing an attribute that it previously could miss.
* Config file parsing, connection parameter extraction and calendar lookup are now delegated to the caldav library instead of being duplicated in plann.  (The caldav library adopted this code from plann a while back; plann was still carrying its own copy.)  Visible side effects: environment variable references like `${SOME_VAR}` or `${SOME_VAR:-default}` in config values are now expanded, and a `features` key is resolved through the caldav library's profile lookup.

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
