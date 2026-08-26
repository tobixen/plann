This was internal meeting notes with my rubber duck long ago, when doing the panic planning algorithm.  It's been in the repository as an untracked file for ages.

* Overdue has to be dealt with before.  Start with the lowest priority (highest number) and offer to procrastinate all overdue, all near-due and all others

* the panic algorithm should have an end time, default "in 30 days"?
* we should have some hours_per_day, max number of hours we can work per day.  Defaults to 4?  Max 24.
* load all events for the period, sorted by dtstart
* create "mock" events with "free time" and inject into the same list
* for all priorities 1 ... 9 ...
*   for all (selected) tasks with given priority, reverse sorted by due ...
*     go through available time slots reversively, starting from the due and ending up at now
*     calculate the required slack time (`task_duration*(24-hours_per_day)/241), add it to slack balance
*     for a free time slot not big enough to accomodate the full task ...
*        if we have slack balance, use the time slot for slack, otherwise ignore it.
*     for a free time slot big enough to accomodate the full task ...
*       if `slot_time` > `task_duration` + `slack_balance`, then inject the slack time balance at the end of the time slot and task right before it.
*        else, put task at the start of the time slot, the rest of the time slot is slack, and we get a negative slack balance
*   if we're at the head of the period ("now"), then ... time to panic!  Offer to procrastinate all tasks with same or higher priority
