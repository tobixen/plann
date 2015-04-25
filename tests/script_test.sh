#!/bin/bash

## Sorry - I have no idea how much of this script is compatible with
## POSIX shell and how much is bashisms ... been using bash for too
## long.

set -e

## SETUP

error() {
    echo "$1"
    exit 255
}

[ -x ./calendar-cli.py ] && calendar_cli=./calendar-cli.py
[ -x ../calendar-cli.py ] && calendar_cli=../calendar-cli.py
[ -z "$calendar_cli" ] && error "couldn't find ./calendar_cli.py nor ../calendar_cli.py"

calendar_cli() {
    echo "    $calendar_cli $@"
    output=$($calendar_cli "$@")
    [ -z "$output" ] || echo $output
}


## TESTING

echo "## testing $calendar_cli"
echo "## this is a very simple test script without advanced error handling"
echo "## if this test script doesn't output 'all tests completed' in the end, something went wrong"

echo "## Attempting to add a past event at 2010-10-09 20:00:00, 2 hours duration"
calendar_cli calendar add '2010-10-09 20:00:00+2h' 'testing testing'
uid=$(echo $output | perl -ne '/uid=(.*)$/ && print $1')
echo "## Attempting to add a past event at 2010-10-10 20:00:00, CET (1 hour duration is default)"
calendar_cli calendar add '2010-10-10 20:00:00+01:00' 'testing testing'
uid2=$(echo $output | perl -ne '/uid=(.*)$/ && print $1')
echo "## Attempting to add a past event at 2010-10-11 20:00:00, CET, 3h duration"
calendar_cli calendar add '2010-10-11 20:00:00+01:00+3h' 'testing testing'
uid3=$(echo $output | perl -ne '/uid=(.*)$/ && print $1')
echo "## OK: Added the event, uid is $uid"

echo "## Taking out the agenda for 2010-10-09 + four days"
calendar_cli calendar agenda --from-time=2010-10-09 --agenda-days=4
echo $output | { grep -q 'testing testing' && echo "## OK: found the event" ; } || echo "## FAIL: didn't find the event"

echo "## Taking out the agenda for 2010-10-10, with uid"
calendar_cli calendar agenda --from-time=2010-10-10 --agenda-days=1 --event-template='{dstart} {uid}'
echo $output | { grep -q $uid2 && echo "## OK: found the UID" ; } || echo "## FAIL: didn't find the UID"

echo "## Deleting events with uid $uid $uid1 $uid2"
calendar_cli calendar delete --event-uid=$uid
calendar_cli calendar delete --event-uid=$uid2
calendar_cli calendar delete --event-uid=$uid3
echo "## Searching again for the deleted event"
calendar_cli calendar agenda --from-time=2010-10-10 --agenda-days=1
echo $output | { grep -q 'testing testing' && echo "## FAIL: still found the event" ; } || echo "## OK: didn't find the event"

echo "## all tests completed"
