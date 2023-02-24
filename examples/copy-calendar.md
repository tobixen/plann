# Copy everything from one calendar to another

I was migrating from one calendar server to another, and needed an easy way to copy all events over.  The method described here does involve quite some CPU overhead ... but for normal-sized calendars, on almost any device or VM in 2023, this should be insignificant.

## Full command

```bash
plann select print-ical | plann --config-section new-calendar add ical
```

## Sub-task: take out all data in raw ical from the calendar

`plann` without any options will select the default calendar from `.config/calendar.conf`.

`plann select` without any options will select everything.

`plann select print-ical` will print all the data to STDOUT.

## Sub-task: insert all the data into the new calendar

`plann add ical` will add raw ical data to a calendar.  You would typically like to add options like `--ical-data=...` or `--ical-file=...`, but if it's not given, then it will default to collect data from STDIN.

## Variants

(None of this was tested)

Copy all events, ignore tasks:

```bash
plann select --events print-ical | plann --config-section new-calendar add ical
```

Copy only uncompleted tasks:

```bash
plann select --todo print-ical | plann --config-section new-calendar add ical
```

Copy only future events:

```bash
plann select --event print-ical --from=$(date +%F) | plann --config-section new-calendar add ical
```

Copy everything, but without a config files:

```
plann --caldav-url=https://example.com/dav/ --caldav-user=peter --caldav-pass=hunter2 --caldav-proxy=socks5://localhost:1080 --calendar-name='Calendar' select print-ical |
  plann --caldav-url=https://newcal.example.com/ --caldav-user=peter --caldav-pass=hunter3 add ical
```
