# User guide for plann v1.0

NB!  Commands here are not very well tested, and it was written before the 1.0-release, so the actual interface may have changed a bit.  It's needed with automated tests verifying that all the commands here work.  And it's needed with YOUR help to test out things and report bugs!

## Command structure

Commands are on this format:

```bash
plann --global-options command --command-options subcommand --subcommand-options
```

The most up-to-date documentation can always be found through `--help`, and it's outside the scope of this document to list all the options.

```bash
plann --help
plann command --help
plann command subcommand --help
```

## Main commands

* list-calendars - verify that it's possible to connect to the server(s) and show the calendar(s) selected
* add - for adding things to the calendar(s)
* select - for selecting, viewing, editing and deleting things from the calendar(s).

## Convenience commands

Those commands are made mostly for making `plann` more convenient to use for the primary author of the tool.  They may perhaps not be useful at all for you, YMMV.  I may eventually decide to "hide" the more obscure commands from the `--help` overview.  (TODO: figure out if subcommands can be grouped in the help printed by click)

* agenda - list up some of the upcoming events plus some of the upcoming tasks
* interactive manage-tasks - go through your tasks and make suggestions
* interactive update-config - (TODO: NOT IMPLEMENTED YET).  This one is not used by the primary author and is probably under-tested.  Its primary intention is to make it easy for others to use the tool.

Note that many of those commands have only been tested on DAViCal (see the [`CALENDAR_SERVER_RECOMMENDATIONS.md`](CALENDAR_SERVER_RECOMMENDATIONS.md) file)


## Global options

The global options are for setting the connection parameters to the server and choosing what calendar(s) to operate at.  Connection parameters may be typed in directly:

* `--caldav-*` to set the server connection parameters
* `--calendar-*` to choose a calendar.  If nothing is specified, the first calendar found will be utilized (on some calendar servers, this will be the default calendar).  It's possible to specify those parameters multiple times.

It's recommended to rather use a config file.  Those options can be used for specifying a config file:

* `--config-file`
* `--config-section`

The default is to utilize the `default` section under `$HOME/.config/calendar.conf`  Here is an example configuration file:

```yaml
---
work-calendar:
  caldav_url: "http://acme.example.com/caldav/"
  caldav_user: drjekyll
  caldav_pass: pencilin
  calendar_url: mycalendar
work-appointments:
  inherits: work-calendar
  calendar_url: mypatients
private-calendar:
  caldav_url: "https://ecloud.global/remote.php/dav/"
  caldav_user: mrhyde
  caldav_pass: hunter2
  calendar_name: goodgames
sinuous-deeds:
  inherits: private-calendar
  calendar_name: badgames
work:
  contains: [ 'work-calendar', 'work-appointments' ]
private:
  contains: [ 'private-calendar', 'sinous-deeds' ]
```

(TODO: the example above haven't been tested)

Multiple config sections can be specified, which may be useful for selecting things from multiple calendars.

## Adding things to the calendar

Generally it should be done like this:

```
plann add ical --ical-file=some_calendar_data.ics
plann add event --event-options 'New years party' '2022-12-31T17:00+8h'
plan add todo --todo-options 'Prepare for the new years party'
plann add journal --journal-options "Resume from the new years party" 2022-12-31 "It was awesome.  Lots of delicous food and drinks.  Lots of firework."
```

Most often, no options should be given to the command `add` - with the exception if one wants to add things to multiple calendars in one command.

Most of the options given after the subcommand are for populating object properties like location, categories, geo, class, etc.

## Selecting things from the calendar

```
plann select --selection-parameters select-command
```

It's usually a good idea to start with the select-command `list`, for instance:

```
plann select --todo --category computer-work list
```

Some calendar server implementations require  `--todo` or `--event` to always be given when doing selects, others not.

### Listing objects

Events can either be output as ics, or through a template.

The templating engine is built on top of the python `string.format()`.  To learn the basics of `string.format()`, w3schools has some nice interactive thing on the web, https://www.w3schools.com/python/ref_string_format.asp

All or almost all icalendar fields should be available.  In addition, the `calendar_name` and `calendar_url` (lower case!) is available (and may be useful when listing content from several calendars).

Text fields can be accessed directly i.e. like this:

```
plann select --todo list --template='{SUMMARY} {DESCRIPTION} {LOCATION}'
```

Dates can be accessed through the dt property, and can be formatted using strftime format, like this:

```
plann select --event list --template='{DTSTART.dt:%F %H:%M:%S}: {SUMMARY}'
```

If a property is missing, the default is to insert an empty string - but it's also possible to put a default value like this:

```
plann select --event list --template='{DTSTART.dt:%F %H:%M:%S}: {SUMMARY:?(no summary given)?}'
```

It's even possible to make compounded defaults, like this:

```
plann select --todo list --template='{DUE:?{DTSTART.dt:?(Best effort)?}?:%F %H:%M:%S}: {SUMMARY:?(no summary given)?}'
```

One thing that may be particularly useful is to take out the UID fields.  With UID one can be sure to delete exactly the right row:

```
plann select --todo list --template='{UID} {SUMMARY}'
```

### Printing a UID

The subcommand `print-uid` will print out an UID.  It's for convenience, the same can be achieved by doing a `select (...) --limit 1 list --template='{UID}'`

### Editing and deleting objects

```
plann select --todo --uid=1234-5678-9abc delete
plann select --todo --category computer-work --start=2022-04-04 --end=2022-05-05 edit --complete
plann select --todo --category computer-work --overdue edit --postpone=5d
```

## See also

[NEW_CLI.md](NEW_CLI.md) is a longer, but possibly less up-to-date document containing some visions of the new `plann`-command.
[NEXT_LEVEL.md](NEXT_LEVEL.md) describes some of my visions on what a good calendaring system should be capable of, and does an attempt on mapping this down to the icalendar standard.
