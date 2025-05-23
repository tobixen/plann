# plann - the "next level" calendar-cli

plann should be a full-featured tool for calendar management, project management and time tracking

This document is dedicated to my rubber ducky - but if anyone else has the patience to read through it, feedback is appreciated.

## Tasks vs events vs journals

In my paradigm, a task is a planned activity that should be done, but not at a specific time (but possibly it should be done within a specific time interval).  When it's done - or when it is deemed irrelevant to do it - it can be striken out from the list.  An event is something that should be done at a relatively well-defined time.  While you may come an hour early or late to the Saturday night party and still have a lot of fun - if you come at the wrong date, then there won't be a party.

It's not always black and white - events may be task-alike (like an appointment that will have to be rescheduled if you miss it) and tasks may be event-alike (i.e. with a very hard due-time and that cannot be done long time before the due date).

Both events and tasks generally contain information about future plans, journals contain information about the past.

## Some potential requirements from a good calendaring system:

* 100% of all calendar users wants the possibility to "strike out" a thing from a calendar (I heard it at the CalendarFest event, so it must be true - though it does break with my paradigm).

* It may be useful to take meeting notes directly from a calendar application (it was also said at the CalendarFest).

* Project management and accounting systems needs information on time estimates and tracking the time spent working on a task (this is a matter of fact).  Project management and accounting systems ought to be tightly coupled with the calendar system (that's my opinion).  How much time does one expect a task to take, and how much was spent on the task?  How many of the hours spent on the tasks should be billed (and how many of those should be billed at over-time rates?).  Should the employee get paid at normal rates or overtime rates for the working hours spent?

* Recurring tasks is a very useful thing! (this is my personal opinion, also ref the [TASK MANAGEMENT document](TASK_MANAGEMENT.md))  Some of them should be done at a fixed time, no matter when it was done previous time, i.e. "prepare gym bag for my sons gym class" should be done every Tuesday, with deadline Wednesday morning.  At the other hand, the task "clean the floor" should typically be done one week after it was done previous time.

* In my opinion (ref TASK_MANAGEMENT), it makes sense on a daily basis to take out relatively short sorted list of tasks, look through it and keep the list short by procrastinating the things that seems less urgent.  I've been using the DTSTART attribute for such procrastination, but it feels a bit wrong.

* For collaboration, it's important to check when participants have available time, as well as to be able to invite participants to calendar entries, and to be able to reply to invitations in such a manner that the event both appears on the personal calendar and that the organizer gets notified on whom will participate.

* The calendaring system should be able to assist with time tracking.  After doing some research on solutions out there,  I've come up with those thoughts:
  * Time tracking information should be available in a standard format to any app that needs it.  It seems perfect to store it as calendar data.  The icalendar standard does not currently 

## Standards as they are now:

### Calendar resource object types

The RFC specifies three different kind of calendar resource object types, it's the VJOURNAL, VTODO and VEVENT.  From a technical point of view, the differences are mostly in what timestamps the object holds.  The VEVENT has a DTEND, the VTODO has a DUE, and the VJOURNAL ... has neither.  The VEVENT is generally expected to have a DTSTART.  The VJOURNAL is generally expected to have a DTSTART set to a date.  A VTODO need not have a DTSTART.  There is also the STATE field that can have different values depending on the object type.  I think all other differences enforced by the RFC is minor.

Calendaring systems usually have very different user interfaces for tasks and events (and journals are generally not used).  Generally, tasks can be "striked out", but they don't stick very well to the calendar.  None of the three types are well-suited for tracking the time spent working on a task or attending to a meeting.

VJOURNAL entries on a calendar is the correct place to store meeting notes ... probably as well as recording things like who was really participating in an event.  It can also be used for recording a diary or make other notes on what one has done during the day.

VEVENT and VTODO is generally optimized for keeping information about the future - while VJOURNAL is supposed to be used for keeping information about the past.  However, the RFC is not explicit on this, and I haven't heard of any implementations that denies one creating tasks/events with timestamps in the past nor journals with DTSTART in the future.

### More on timestamps

A VJOURNAL can only contain a DTSTART, and no DURATION or DTEND.  This makes it impossible to use the VJOURNAL to track how much time has been spent.  I think this is stupid - as written above, time tracking is something we would like to do at the calendar level, and since it's information on things that has already happened, VJOURNAL is the most logic place to put it.

A VTODO may have a DTSTART and a DUE.  I think the DUE timestamp is relatively easy to define, it's the time you, your leader, your customer and/or your significant other and/or other relevant parties expects the task to be completed.  It may be a hard deadline, or it may be a "soft" target that may be pushed on later.  The DTSTART is however a bit more tricky, I can see the field being used for quite different purposes:

* The earliest possible time one can start working with a task (or the earliest possible time one expects to be able to start working with it)
* The time one is actually planning to start working with it
* The latest possible time one can start working with it, and still be done before the due time.
* The time one actually started working with the task

As an example, consider a tax report to be filled out and sent to the authorities, the latest at the end of April.  Consider that one will have to pay fines if it is not delivered before midnight the night before 1st of May.  One cannot start with it before all the data one needs is available, perhaps 1st of April is the earliest one can start.  One may plan to work with during a specific Sunday in the middle of April.  If it takes three hours to complete the report, the very latest one can start is at 21:00 night before the 1st of May, but it would be very silly to actually start at that time.  And perhaps one actually got started with it at noon at the 25th of April.

A VEVENT and a VTODO may take a DURATION, but it cannot be combined with DTEND or DUE.  While the RFC is not explicit on it, it is my understanding that DURATION and DTEND/DUE is interchangable - if DTSTART and DTEND/DUE is set, the DURATION is implicitly the difference between those two - an object with DTSTART and DURATION set is equivalent with an object with DTSTART and DTEND/DUE set.  For the rest of the document, DURATION is understood to be the difference between DTSTART and DTEND/DUE.  In my head, tasks have a DUE and a DURATION while the DTSTART is a bit more abstranct.  Hence, setting or changing the DURATION of a task may efficiently mean "setting the DTSTART" - and the definition of DTSTART depends on the definition of DURATION.  Is the DURATION the time estimate for completing the task?  Then DTSTART will have to be the very latest one can start with the task and still complete before the DUE.

Other observations:

* It is possible to specify that a task should be a recurring task, but there is no explicit support in the RFC of completing an occurrence.  In the existing version of calendar-cli, a new "historic" task instance is created and marked complete, while dtstart is bumped in the "open" task.  (there is an alternative interpretation of "recurring task", it could mean "let's work on project A every Tuesday after lunch, all until it's completed").

* Calendar components can be linked through the RELATED-TO-attribute.  Valid relationship types are "CHILD", "PARENT" and "SIBLING".  I suppose it is intended for direct asyclic graphs, where a calendar component preferably should have only one PARENT, and where there shouldn't be loops (my grandchild cannot possibly also be my grandparent) - and that two SIBLINGs have the same PARENT. (When writing this, I was not aware of RFC9253).

* RFC6638 gives a framework for inviting and replying to calendar events ("scheduling"), but few calendar servers supports it fully.

## Suggestion for work flow and use (or abuse?) of the icalendar standard:

### Sticking a task to the calendar

One may have an agenda with lots of events and some "unallocated" time in between, and one may want to try to plan getting specific tasks done at specific times.  It may be nice to get this into the calendar.

If a task has a DTSTART set, it may be interpreted as the time one actually plan to start working with the task - but it's non-ideal, for one thing most calendaring user interfaces will not "stick" the task to the calendar on that, and the DTSTART attribute may be used for other purposes.

It may make sense to make a VTOOD stick to the calendar by making up a VEVENT and letting that VEVENT be a child of the VTODO.

Similarly, for calendar items that "needs" to be "striken out" (say, some course you need to take - if you miss the scheduled course time then you need to take it at a later time), it may make sense to create a "parent task" for it.

Perhaps even make it to a general rule that all activities should be registered on the calendar as a VTODO/VEVENT parent/child pair, where the VTODO contains time estimates and the VEVENT contains planned time for doing the VTODO.

### Time tracking

Time tracking should be an integrated part of a good calendaring system.  Sadly, time tracking does not fit neatly into the iCalendar format as of today.  I'd love to see an update to the standard for this.

The three best solutions I can think of is:

* Add an optional DTEND and/or DURATION property to JOURNAL entries (as those are meant to be used to record the past, while VEVENT and VTODO is meant to plan the future).  (This is probably a no-go - for decades in the future, people will be using legacy software where the DTEND would not pass validation)
* Add another participant status (PARTSTAT), ATTENDED (but great care should be taken, one may not always want to notify event organizers that one participated in an event).
* A separate calendar component type, like VTIMESPENT.

I've been thinking relatively deeply about this - and considered that while waiting for better standards the best solution is to be using PARTSTAT=X-ATTENDED.  For personal time tracking, it may be important to make a personal copy of the event ensuring status updates are not sent to the organizer.

### Striking out something from the calendar

The considerations above sort of leaves us with two ways of "striking out" something.  There is the traditional way of marking the task as COMPLETED.  Now if the task is connected to a VEVENT, the calendar item should also be striken out.

The second way is to make sure there is a VJOURNAL attached as a child of the VEVENT or a (grand)grandchild of the VTODO.

Those two ways of striking out things have fundamentally different meanings - the first is to mark that a task is done and closed and does not need to be revisited, the second is to mark that work time was spent on the task or event.  This may be combined in different ways;

* If one did some work and completed a tas, one would typically want to use both kind of "strikes".
* Sometimes one may want to mark a task as "completed" or "cancelled" even if one hasn't spent time on it - maybe because it has become irrelevant or because it has already been done (by someone else, or the work has been "piggybacked" in another task, time consumption counted for in another project, etc)
* Sometimes one has spent time on a task without completing it (maybe partly completed, maybe wasted some time on it before marking it as "cancelled", etc), then one would like to create the journal entry but without marking it as complete.

### Task management

* A VEVENT linked up as a child to a VTODO means we've (tried to) allocate some time for doing the VTODO (hence "sticking" the task to the calendar).  If the task isn't marked completed by the end of the event, the calendar system should point it out.  The user should then either reschedule, procrastinate, cancel, mark it as completed, or mark it as partially done.

* A VEVENT linked up as a parent to a VTODO means the VTODO needs to be completed before the event.  Once the event has passed, the VTODO should probably be cancelled if it wasn't done yet.

* A VTODO (A) linked up as a parent to another VTODO (B) means either that B is a subtask of A or that A depends on B.  In either case, B needs to be completed before A can be completed.

* DURATION (efficiently meaning DTSTART, when DUE is set) should be used for time estimates (this breaks with my previous usage of DTSTART as the earliest time I would expect starting to work on the task).  In the case of child/parent tasks, DURATION should (probably?) only indicate the "independent" time usage - so the full estimate of the time consumption for the whole project is the sum of the duration of all the VTODOs in the project.  This may be a bit silly, as it either means the DUE for the "root task" must be set almost at project start (though, it may make sense if planning things in a top-down fashion), or that the DTSTART for the "root task" must be set almost at the project end (may make sense when considering dependencies - the subtasks needs to be done first).

* PRIORITY should indicate how important it is to do the task by the indicated DUE date/timestamp.  If PRIORITY=1, then the task is extremely important AND the DUE is a hard deadline.  PRIORITY=9 may mean either that DUE is a "fanciful wish" OR that the task should simply be cancelled if it's difficult to get it done prior to the DUE date.

* The calendaring system should make it possible to sort tasks based on the ratio between duration and available time until due date, and show tasks that ought to be prioritized during the next few days.

* The calendaring system should make some simple-stupid algorithm to predict the "load", how likely one is to manage the upcoming due dates.  Some parameters can be given, i.e. that one expects to be able to spend 2 hours a day for this category of tasks during the next 30 days and that tasks with priority 7 or higher can be ignored.

* If the upcoming task list is too daunting, it should be possible to semiautomatically procrastinate (move the due) upcoming items based on their priority.

* Recurring tasks is still a potential problem.

## The new plann interface

This section has been moved to a separate document, [`NEW_CLI.md`](NEW_CLI.md)

