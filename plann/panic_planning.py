from dataclasses import dataclass
from datetime import datetime, timedelta
from sortedcontainers import SortedKeyList
from plann.lib import _ensure_ts, _now

class TimeLine(SortedKeyList):
    """
    The TimeLine is a sorted list of dicts, the dict should as the very minimum contain the datetime key begin.

    The TimeLine should be without holes.  Unallocated time should be presented as a dict with only the key begin (which should correspond to the end of the previous item on the timeline)

    The TimeLine should not contain overlapping events.
    """
    def __init__(self):
        SortedKeyList.__init__(self, key=lambda x: x['begin'])

    def count(self):
        """Includes all real objects on the list.  Ignores start and end markers, as well as slack"""
        return len([x for x in self if 'obj' in x and x['obj'] != 'slack'])

    def add_event(self, event):
        start = event.icalendar_component.get('dtstart')
        end = event.get_dtend()
        if not end and start and not isinstance(start.dt, datetime):
            end = start.dt + timedelta(days=1)
        if not end or not start:
            ## Todo: consider DURATION ...
            return
        start = _ensure_ts(start)
        end = _ensure_ts(end)
        self.add(start, end, event)

    def add(self, begin, end, obj=None):
        assert(begin.tzinfo)
        assert(end.tzinfo)
        obj_ = {'begin': begin, 'obj': obj}
        assert end > begin
        i = self.bisect_right(obj_)
        if i<len(self):
            ## No overlapping accepted
            assert self[i]['begin'] >= end
        if i>0:
            assert not any(key != 'begin' for key in self[i-1])
        if i>0 and i<len(self):
            if self[i-1]['begin'] == begin and self[i]['begin'] == end:
                self[i-1]['obj'] = obj
                return
        SortedKeyList.add(self, obj_)
        if i+1==len(self) or self[i+1]['begin'] > end:
            SortedKeyList.add(self, {'begin': end})

    def get(self, ts):
        if not (len(self)):
            return {'begin': ts}
        i = self.bisect_left({'begin': ts})
        if i>0:
            foo = self[i-1].copy()
        else:
            foo = {}
        if i<len(self):
            foo['end'] = self[i]['begin']
        return foo

    def find_opening(self, last_possibility, duration, slack_balance=timedelta(0)):
        end = last_possibility-duration
        while True:
            foo = self.get(end)
            if len(foo) == 2:
                if 'end' in foo and 'begin' in foo:
                    foodur = foo['end']-foo['begin']
                    if foodur > duration:
                        return (foo, slack_balance)
                    slack_balance += foodur
            if not 'begin' in foo or not 'end' in foo:
                return (foo, slack_balance)
            end = foo['begin']-timedelta(seconds=1)

    def pad_slack(self, end, duration):
        i = self.bisect_left({'begin': end})-1
        while i>=0 and duration>timedelta(0):
            if any(key != 'begin' for key in self[i]):
                end = self[i]['begin']
                i -= 1
                continue
            slot_dur = end - self[i]['begin']
            if slot_dur <= duration:
                duration -= slot_dur
                self[i]['obj'] = 'slack'
            else:
                self.add(end-duration, end, 'slack')
                duration = timedelta(0)
        if duration:
            self.add(begin=end-duration, end=end, obj='slack')

def timeline_suggestion(ctx, hours_per_day=4, timeline_end=None):
    timeline = TimeLine()
    objs = ctx.obj['objs']
    events = [x for x in objs if 'BEGIN:VEVENT' in x.data]
    event_parents = []
    for event in events:
        comp = event.icalendar_component
        if comp.get('STATUS', '') == 'CANCELLED':
            continue
        ## TODO: get_relatives refactoring
        if 'RELATED-TO' in comp and event.get_dtend()>_now():
            rels = comp['RELATED-TO']
            if not isinstance(rels, list):
                rels = [ rels ]
            for rel in rels:
                if rel.params.get('RELTYPE') == 'PARENT':
                    event_parents.append(str(rel))
    tasks = [x for x in objs if 'BEGIN:VTODO' in x.data]
    assert len(events) + len(tasks) == len(objs)
    tasks = [x for x in tasks if ('\nDUE' in x.data or '\nDURATION' in x.data) and '\nDTSTART' in x.data]
    
    for event in events:
        if not 'BEGIN:VEVENT' in event.data:
            continue
        ## TODO ... we should handle overlapping events a bit better than just ignoring AssertionErrors
        try:
            timeline.add_event(event)
        except AssertionError:
            pass
    tasks.sort(key=lambda x: (x.icalendar_component.get('PRIORITY',0), _now()-_ensure_ts(x.get_due())))
    slackbalance = timedelta(0)
    for task in tasks:
        if str(task.icalendar_component['UID']) in event_parents:
            ## task is presumably already included in timeline
            continue
        due = task.get_due()
        if due is None:
            due = timeline_end
        end = _ensure_ts(due)
        if timeline_end:
            end = min(end, timeline_end)
        duration = task.get_duration()
        slackbalance -= duration*(24-hours_per_day)/hours_per_day
        slot, slackbalance = timeline.find_opening(end, duration, slackbalance)
        if 'end' in slot:
            end = min(end, slot['end'])
        begin = end - duration
        timeline.add(begin, end, task)
        if slackbalance<timedelta(0):
            timeline.pad_slack(begin, -slackbalance)
            slackbalance=timedelta(0)
    return timeline    
