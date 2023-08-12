# Changelog

Development on 0.x is going on fast-paced and erratic, with the
priority of getting a tool the author can use for his daily planning.
Changelogs will be kept rather minimalistic until v1.0 has been
released.  Since this technically is a fork of calendar-cli (though
almost everything is written from scratch), release v0.15.0 is like
the first proper release.

The format of this file is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and I do try to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixes

* More comments, mostly in the functional test

## [v0.15.1] - 2023-07-20

Summary: Misc bugfixes

### Fixes

* Things added to the calendar would often bypass the `tz.store_timezone` configuration (defaulted and recommended to be UTC), and rather be stored in the `tz.implicit_timezone` (defaulted to local timezone).  Since the local timezone often does not have a valid TZ-identifier (and also, according to the RFC, any non-UTC timezone has to be specified in the icalendar objects), tests would randomly fail dependent on the timezone on the computer running the tests.  Credits to github user @fauxmight for reporting, fixed in https://github.com/tobixen/plann/pull/8
* Fixes for various other bugs, introduced due to rough development practices for the 0.x-branch.  Included in  https://github.com/tobixen/plann/pull/8

## [v0.15.0] - 2023-07-19

First release of plann (as of v0.14 it was a part of calendar-cli).  Development up until v0.15 has been fast-paced and erratic, prioritizing to "get things to work out well enough for the author".  The tool works for me, but has plenty of rough edges.
