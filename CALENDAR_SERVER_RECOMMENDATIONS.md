# What CalDAV-server to choose?

TLDR-summary: Choose DAViCal - though, if you're going to self-host it, then be aware that it involves some work to set it up.  You may also consider Radicale and  SOGo.

## Requirements

To be able to efficiently use `plann` version 1.0 (no, it has not been released yet - work in progress) for planning, you will need a calendar server that supports ...

* Tasks (VTODO component type)
* Searching on text fields
* Searching on categories
* Recurring events
* Recurring tasks

Also, I have on the long term list to also make it easy to add journal entries after a meeting has been held or a task has been done - then the calendar should also support the VJOURNAL component type.

Perhaps at some point in the future, I will also add support for "scheduling" (basically, sending meeting invites and respond to them).

## Different servers tested (self-hosting)

### DAViCal

DAViCal seems to be one of the most standard-compliant caldav servers out there, and it has been around for quite a while.  It supports everything we need, even scheduling.  It has a basic WebUI for administrating access rights, users, etc.  It also supports address books (VCARD).

It's written in PHP, needs a database backend (PostgreSQL) and a webserver frontend (Apache is probably easiest - though I went for php-fpm and nginx).

I installed a version a decade ago, didn't upgrade it ever, and it worked out well enough.  While tossing out obsoleted hardware, obsoleted ISP, etc, I tried reinstalling it on Archlinux, 2023.  It was not a very pleasant experience.  As of 2023-01, I would recommend disregarding the article on the Archlinux wiki completely (https://wiki.archlinux.org/title/DAViCal - well, it's a Wiki, I should probably improve on it).  I got version 1.1.10 installed, and it was not even possible to create users - due to a bug that was fixed in 1.1.11.  I found another showstopping bug (https://gitlab.com/davical-project/davical/-/issues/280) but managed to work around that one.  Huff.

### Radicale

https://radicale.org/

Also a relatively new server, written in Python, though apparently less actively maintained than Xandikos.  It's also included in the test suite of the python caldav library, hence the caldav client library is tested very frequently against Radicale.  It's also very easy to set up.

Radicale also seems to be something that should be considered.  I'm not sure if it supports multiple users, but at least it does not support the scheduling RFC.  It seems like the only showstopper is https://github.com/Kozea/Radicale/issues/1280 - which looks like something that I could probably fix myself if/when I get time for it.

Radicale also supports address books (VCARD).

### SOGo

https://www.sogo.nu/

This is "Groupware" supporting mail and featuring a rich web interface.

SOGo has been around for as long as the python caldav library.

I was earlier dismissing it because of the lack of expand support - though, now the python caldav library can do client-side expand, so it's not important anymore.  I should revisit and test it more thoroughly again.

SOGo did not support journals last time I checked.

### Xandikos

https://www.xandikos.org/

Relatively new server, written in Python, stores all data in a local git-repository.  Super-easy to set up and get started with.  Quite standard-complient.  Compability is ensured, as it's included in the python caldav library test suite, and hence tested almost on every commit.  I would definitely recommend Xandikos if/when it will support recurrances.  The missing support for recurring events and task is a big show-stopper for me.  When this is fixed, I will most likely recommend Xandikos.

Xandikos does not support multiple users and access controls (I would still use it for my family - one calendar for each person, and no personal secrets stored in the calendars).  The lack of multi-user support also means support for scheduling is missing.

Xandikos also supports address books (VCARD).

### Robur

https://github.com/roburio/caldav

Robur is written in ... eh ... what?

It does not support relationship attributes, text search is not working, it does not support journals and some other problems.

### Baikal

https://sabre.io/baikal/

PHP-based application.

I haven't revisited it for a while, but Baikal does not support recurring tasks.  I think recurring tasks are important, but if you disagree you may probably try Baikal.

Baikal has problems with synchronizing (through sync tokens) breaking if something got deleted from the calendar.

### Nextcloud

https://www.nextcloud.com/

Nextcloud has a lot of components, including calendar.

I believe the calendar is based on Sabre, at list my list of problems is roughly the same as for Baikal.

### Zimbra

"Groupware", supporting mail and featuring a rich web interface.

If you're already using Zimbra, then by all means - you may try, and you may be lucky.  I do use plann against Zimbra myself - but it's not my primary calendar, and it also seems like they're breaking their CalDAV support little by little for every release.

On my list (some of it is old, I haven't bothered to recheck):

* Zimbra does not support journal entries
* Setting the "display name" of a calendar through CalDAV does not work
* It's not possible to do a simple GET towards a calendar component resource
* Zimbra has a very clear distinction between a "task list" and a "calendar", one cannot combine tasks and events on the same calendar.
* Sync tokens not supported
* Category search yields nothing
* Relationships cannot be set
* Quite some other minor issues

### Bedework

"Bedework Enterprise Calendar System" is the title of https://www.bedework.org/ - but the web site there looks like it was written in 1990.  It does point to more enterprise-looking web pages though.  Java-based.

I haven't revisited this one, but when testing it long long time ago it didn't support tasks nor journals nor recurrances, so it is (or was?) a no-go.

## Calendar-as-a-service providers

(This section should probably be improved and expanded)

* Robur is offered as a cloud service - https://calendar.robur.coop/
* Fastmail does not support tasks and some other problems.  They also did not allow me to have a dedicated permanent test account for free, so I haven't done more testing.
* ecloud.global offers NextCloud
* Google had quite limited CalDAV support, and did not support tasks last time I checked
* iCloud does not officially support CalDAV - unofficially they do have some quite broken CalDAV-support, with no support for recurrances nor tasks and many other things are broken.

## Non-free solutions

* Synology does not support recurring tasks

## Things I should consider testing for

* Possibility to add tasks and events to the same calendar.  I know most servers supports it and that Zimbra does not support it, but should explicitly test this on all the servers.
* Possibility to ask for events and tasks in the same report query.  This is important for plann, as this is the default search mode.  For xandikos, one has to explicitly add --todo or --event to get anything from a search.  I should check if this is the same for other implementations.
