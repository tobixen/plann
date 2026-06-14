# Code review — plann

This code review was started with the Fable model, but the model [got yanked](https://www.anthropic.com/news/fable-mythos-access) pin the middle of the process, so the rest was done with Opus.  That's sad, the whole point of asking for a code review was to utilize the Fable model.

- **Date:** 2026-06-13
- **Branch:** `refactor/delegate-config-to-caldav`
- **Commit:** `3e746c4`
- **Scope:** Full review of the `plann/` package (`lib.py`, `cli.py`, `commands.py`,
  `interactive.py`, `panic_planning.py`, `timespec.py`, `config.py`, `template.py`).
- **Method:** 7 independent finder passes (line-by-line, removed-behavior,
  cross-file, reuse, simplification, efficiency, altitude), then each correctness
  candidate re-verified by reading the cited code.

Findings are grouped: confirmed correctness bugs first (ranked most-severe), then
cross-cutting cleanup / altitude / efficiency themes.

---

## Correctness bugs

### 1. `add-time-tracking` subcommand crashes on every invocation — `cli.py:192`

```python
@click.option('startnow/track', help="...", default=True)
```

The option name is missing its leading dashes (`--startnow/--track`). Click rejects
this with `ValueError: Invalid start character for option (startnow)` as soon as the
command parser is built, so `plann select ... add-time-tracking` — even
`add-time-tracking --help` — exits with an error and the feature is completely
unreachable.

**Fix:** `@click.option('--startnow/--track', ...)`.

**Human comment:** This feature was added in my working directory long ago, heavily used, but only through the interactive menus.

### 2. `select --no-pinned-tasks --todo` raises `NameError`/`AttributeError` — `commands.py:160-162`

```python
if isinstance(obj, caldav.Todo) and not pinned_tasks:
    _relships_by_type(obj, 'CHILD').get('CHILD',[])          # result discarded
    if not any(x.icalendar_comp.get('STATUS', '')!='CANCELLED' for x in parents if isinstance(x, caldav.Event)):
```

Two bugs in two lines:
- Line 161 computes the child relations but throws the result away.
- Line 162 iterates `parents`, which is only ever bound in the *Event* branch
  (line 153). For the first `Todo` in the loop `parents` is undefined → `NameError`;
  if an Event was processed earlier the **stale** `parents` from that Event is used.
- `x.icalendar_comp` is a typo for `x.icalendar_component` → `AttributeError`.

The intent was presumably `children = _relships_by_type(obj, 'CHILD').get('CHILD',[])`
followed by a check over `children`.

### 3. `_relationship_text` only ever shows the first relation type — `lib.py:377`

```python
for reltype in rels:
    objs = []
    for relobj in rels[reltype]:
        objs.append(_summary(relobj))
    ret.append(reltype + "\n" + "\n".join(objs) + "\n")
    return "\n".join(ret)        # <-- indented inside the loop
```

The `return` sits inside the `for` loop, so the function returns after the first
`reltype`. A task with both PARENT and CHILD relations silently shows only one of
them. This text is displayed in `interactive_split_task` right before the user
decides how to split/postpone, so they act on an incomplete picture.

**Fix:** dedent the `return` to function level.

### 4. `_list(..., ics=True)` emits the first object regardless of the filter — `lib.py:441`

```python
if ics:
    if not objs:
        return
    icalendar = objs.pop(0).icalendar_instance   # included unconditionally
    for obj in objs:
        if not filter(obj):
            continue
        icalendar.subcomponents.extend(obj.icalendar_instance.subcomponents)
```

The first object is popped and used as the base instance without ever calling
`filter(obj)`. If the filter would reject `objs[0]` (e.g. an interactive selection
that excludes completed tasks and the first task happens to be completed), it is
exported anyway.

**Fix:** apply `filter` to the first object too — build the base calendar from the
first *accepted* object, or start from an empty calendar and extend for every
accepted object.

### 5. Inverted condition in `interactive_split_task` — never postpones when asked — `interactive.py:336`

```python
postpone = click.prompt("Should we postpone the parent task?", default='0h')
if postpone in ('0h', '0'):
    _procrastinate([obj], postpone, check_dependent='interactive', ...)
```

The procrastinate call fires **only** when the user declines (enters `0h`/`0`) and
is skipped when they enter a real duration like `2d`. The logic is backwards —
compare the correct `not in` test used in `commands.py`. Result: answering `2d`
silently leaves the parent's DUE/DTSTART unchanged; answering the `0h` default does
a pointless zero-postpone.

**Fix:** `if postpone not in ('0h', '0'):`.

### 6. Year duration is ~15 days when there is no base date — `timespec.py:151`

```python
time_units = {
    's': 1, 'm': 60, 'h': 3600,
    'd': 86400, 'w': 604800,
    'y': 1314000                 # == 365*3600, missing the *24 day factor
}
```

`1314000 = 365 * 3600`; the correct value is `365 * 86400 = 31_536_000`. This table
is only consulted in the `dt is None` branch (the dated branch is special-cased at
line 163), so `parse_add_dur(None, '1y')` returns `timedelta(seconds=1_314_000)`
≈ 15.2 days — a 24× error.

**Human comment:** Is it needed to reinvent the wheel here?  Doesn't there exist good libraries out there doing the job?

### 7. `parse_add_dur` year branch crashes on a `date` and on Feb 29 — `timespec.py:163-164`

```python
if u=='y' and dt:
    dt = datetime.datetime.combine(datetime.date(dt.year+int(i), dt.month, dt.day), dt.time(), tzinfo=dt.tzinfo)
```

`dt.time()` and `dt.tzinfo` don't exist on a plain `datetime.date`. The guard at
line 146 (`not isinstance(dt, datetime.date)`) treats both `date` and `datetime` as
"already parsed", so a `date` flows straight here. `parse_timespec('2021-01-08+1y')`
where `parse_dt` returned a `date` → `AttributeError`. Separately, a Feb-29 start
date raises `ValueError` in a non-leap target year.

### 8. Multi-unit duration loses all but the last unit when there is no base date — `timespec.py:166`

```python
else:
    diff = datetime.timedelta(0, i*time_units[u])   # reassigned, never accumulated
    if dt:
        dt = dt + diff
...
return diff
```

When `dt is None`, each loop iteration overwrites `diff` instead of accumulating, and
the function returns only the **last** component. `parse_add_dur(None, '1h30m')`
returns 30 minutes, not 90. Reachable via `interactive.py:332`
`parse_add_dur(None, new_estimate)` where the user types e.g. `1h30m`.

**Fix:** accumulate (`total += diff`) across iterations and return the sum.

### 9. Event-only guard in `add-time-tracking` never fires — `cli.py:202`

```python
if not startnow and not all (x for x in objs if isinstance(x, caldav.calendarobjectresource.Event)):
    _abort("original timespan is only allowed for events ...")
```

`all(x for x in objs if isinstance(x, Event))` tests the truthiness of the Event
objects that *survive* the filter, not "are all objects Events". For an all-Todo
selection the generator is empty → `all([])` is `True` → the guard is skipped and
`add_time_tracking_` is called on a Todo with `start_time=None`.

**Fix:** `all(isinstance(x, caldav.Event) for x in objs)`. (Blocked behind bug #1
today, but wrong regardless.)

### 10. `timeline_suggestion` crashes on all-day / DTEND-less events that have relations — `panic_planning.py:112`

```python
if 'RELATED-TO' in comp and event.get_dtend()>_now():
```

`get_dtend()` can return `None` (no DTEND) or a `date` (all-day event); neither can
be compared with the aware `datetime` from `_now()`. An all-day event carrying a
`RELATED-TO` property raises `TypeError: can't compare datetime.datetime to
datetime.date`. This line is **outside** the `try/except AssertionError` that guards
`timeline.add_event`, so the whole panic check aborts.

**Fix:** guard for `None` and normalize date→datetime (e.g. via `_ensure_ts`) before
comparing.

### 11. `interactive check-due --limit` is a string, not an int — `cli.py:519`

```python
@click.option('--limit', help='If more than limit overdue tasks ...')   # no type=int
```

`select`'s `--limit` declares `type=int` (`cli.py:169`), but this one doesn't. The
string flows into `__select`, which does `ctx.obj['objs'][0:limit]`
(`commands.py:191`) → `TypeError: slice indices must be integers`.
`plann interactive check-due --limit 5` crashes.

**Fix:** add `type=int`.

### 12. `obj.icalendar_component_UID` in the inconsistency-logging path — `lib.py:355`

```python
logging.error(f"Inconsistency issue ... (UID={obj.icalendar_component_UID}, ...)")
```

There is no `icalendar_component_UID` attribute (line 351 correctly uses
`obj.icalendar_component['UID']`). When a relative has more than one RELATED-TO
pointing back (`len(back_rel_types) > 1`), the log statement itself raises
`AttributeError` instead of logging — turning a recoverable data warning into a
crash during e.g. `list --top-down`.

### 13. Leftover `breakpoint()` in `_procrastinate` — `lib.py:241-244`

```python
import inspect
stack_depth = len(inspect.stack())
if stack_depth > 13:
    breakpoint()
```

Debugging scaffolding left in. Interactive procrastination of a task with a
postponable parent is easily reached through nested click subcommands with a stack
deeper than 13 frames, dropping the user into `pdb` (or appearing to hang in
non-tty/scripted use). The existing `assert recursivity < 16` already guards runaway
recursion. **Delete the block.**

### 14. `time_tracking` config given as a string iterates per character — `lib.py:165`

```python
time_tracking = getattr(obj.parent, 'extra_config', {}).get('time_tracking')
...
for tt in time_tracking:
    if tt in ('timewarrior', 'Timewarrior', 'timew'):
        ...
    else:
        raise NotImplementedError('Only time tracking through taskw supported so far')
```

The error message at line 158 literally tells the user to set
`time_tracking=timewarrior` — a scalar. A scalar string then gets iterated
character-by-character (`'t'`, `'i'`, ...), none match, and the `else` raises. A
plausibly-correct config crashes. **Fix:** accept a string (wrap in a list) or
document/validate that a list is required.

### 15. `dismiss-panic` double-prefixes its lookahead — `cli.py:538` + `commands.py:466`

`dismiss_panic` (CLI) passes `f"+{lookahead}"` into `_dismiss_panic`, which *also*
does `lookahead = f"+{lookahead}"` at `commands.py:466`, yielding `"++60d"`. The
direct callers at `cli.py:508/510` pass no prefix, so only the CLI command path is
affected. It currently survives only because the duration regex tolerates the extra
`+`; passing `--lookahead='+60d'` would push it to `"+++60d"`. **Fix:** prefix in
exactly one place.

---

## Cleanup / altitude / efficiency

These are not crashes but raise maintenance cost or risk; several were flagged
independently by multiple finder passes.

### Duplication & drift

- **`commands.py:226` — `_interactive_edit` is a stale copy of `interactive.py:208`.**
  `commands.py` already imports many helpers from `plann.interactive`, but keeps its
  own copy of `_interactive_edit`. The two have *already* diverged: the
  `interactive.py` version has the just-ported `start` time-tracking command and
  re-prompts after it; the `commands.py` copy (used by `_check_due` and
  `_dismiss_panic`) does not. The new `start` feature is effectively unreachable
  through those paths. **Delete the copy, import the canonical one.**
- **`commands.py:282` — pdb hand-off block duplicates `interactive.py:88-94`.** Same
  "happy hacking" text + `breakpoint()`. Extract a shared `_pdb_edit(obj)`.
- **`interactive.py:301` — inline summary fallback duplicates `_summary`.**
  `comp.get('summary') or comp.get('description') or comp.get('uid')` re-implements
  the already-imported `_summary`; the two will drift.
- **`interactive.py:153` — `get_obj` helper duplicates `_get_obj_from_line`
  (`interactive.py:366`).** Two line→object parsers with different edge-case
  handling (comment stripping, empty-UID behavior).

### Duration grammar in four places

The `[smhdwy]` relative-duration grammar is encoded separately in
`commands.py:115` (`__select`), `timespec.py:154` (`parse_add_dur`),
`timespec.py:209` (`_parse_timespec`), and `interactive.py:381`
(`_command_line_edit`). Adding the planned month unit (TODO in `parse_add_dur`)
means `--end=+3M` parses in one place and is rejected in another. Export a single
`DURATION_RE` / `is_duration()` from `timespec.py`.

### Component-type detection by raw-string sniffing

`'BEGIN:VTODO' in obj.data` / `'BEGIN:VEVENT' in obj.data` appears across
`commands.py:227`, `panic_planning.py:106/116/121`, `cli.py:404`,
`interactive.py:209`. A single `lib.py` helper using `obj.icalendar_component.name`
(already used at `lib.py:140`) would centralize it; otherwise each new component
type (the VJOURNAL work already touched several of these) means hunting down 7+
scattered checks, and any object whose *description* text contains `BEGIN:VEVENT`
misclassifies.

### `category` vs `categories` special-casing

The singular/plural oddball is special-cased at `lib.py:41`, `lib.py:392-399`
(`_process_set_arg`), `lib.py:418` (`_set_something`), `cli.py:139`, and
`commands.py:558`. Adding another multi-valued attribute (attendee, etc.) needs
synchronized edits in five places across three modules.

### Config-to-caldav migration left half-done

`config.py:45` (`interactive_config`) still hardcodes its own key list
(`caldav_url`, `ssl_verify_cert`, ...) although connecting/parsing was delegated to
`caldav.config` in commit `26dc550`. The writer half already diverges from what
`find_calendars` understands (no `features`, no `time_tracking`/`extra_config` from
commit `45c5c22`). Keys the prompt writes that caldav's extractor drops are silently
ignored at connect time with no error.

### `extra_config` smuggled as a monkey-patched attribute

`find_calendars` (`lib.py:110`) attaches `cal.extra_config` onto caldav Calendar
objects, and `add_time_tracking` (`lib.py:156`) reads it via
`getattr(obj.parent, 'extra_config', {})`. Any calendar object not produced by
`find_calendars` (e.g. `obj.parent` after an `object_by_uid` round-trip) silently
lacks it, so time tracking raises `NotImplementedError` despite correct config. This
per-calendar config should ride through the caldav config/calendar API rather than an
injected attribute.

### Hand-rolled implementations of stdlib / library functions

- **`interactive.py:344` (`_editor`)** re-implements a PATH search that
  `shutil.which(editor)` does in one line — and the hand-rolled version leaves `ed`
  bound to a non-executable fallback when nothing is found, producing a confusing
  `FileNotFoundError`.
- **`lib.py:72` (`_split_vcals`)** splits concatenated VCALENDAR streams by raw
  string scanning at a hard-coded 14-char offset, assuming LF line endings;
  `icalendar.Calendar.from_ical(ical, multiple=True)` (icalendar 5.0.7 is pinned)
  handles CRLF and folding correctly.

### Efficiency

- **`cli.py:94`** — the `cli()` group calls `find_calendars()` (network discovery +
  per-calendar connect) unconditionally, so even `plann --help` connects to every
  configured calendar. Defer discovery to first use.
- **`commands.py:177`** — the sort key rebuilds `Template(skey)` on every comparison;
  compile it once outside `fkey`.
- **`lib.py:348`** — the relationship consistency check does a `get_relatives`
  network round-trip per related object, and `_list` calls `_relships_by_type` per
  listed object, so `list --top-down` over N tasks with R relations issues ~N×R
  extra round-trips. Cache fetched relatives or make the scan opt-in.
- **`commands.py:562`** — `_set_task_attribs` issues a fresh server `_select` per
  attribute (category, due, priority, duration) plus another in `_cats`; fetch once
  and filter client-side.
- **`commands.py:92`** — `--uid` resolution loops `get_object_by_uid` per
  (uid × calendar) and keeps querying after a hit: U×C round-trips for U uids over C
  calendars.

### Dead code

- **`timespec.py:229`** — `raise NotImplementedError("possibly a ISO time interval")`
  is unreachable; every preceding path returns or raises.
- **`interactive.py:58-64`** — `command_edit` checks `if 'with family' in command`
  twice in the same block; the second was probably meant to be `'with parent'`, so
  `postpone 1d with parent` silently does nothing.

---

## Suggested priority

Fix in this order: **#1** (feature dead on arrival), **#2** (crashes a common
listing command), **#5 / #3 / #4** (silent wrong behavior — the dangerous kind),
then the remaining crash-on-edge-case items **#6-#15**. The duplication of
`_interactive_edit` is worth doing early since it currently hides the newly-ported
`start` feature from two command paths.

> Note: filename uses `2026-06-12` per request; the review was actually run
> 2026-06-13.

---

## Fix status (updated 2026-06-13)

| # | Title | Status | Notes |
|---|-------|--------|-------|
| 1 | `add-time-tracking` crashes — missing `--` on option | ✅ Fixed | `cli.py:192` |
| 2 | `--no-pinned-tasks --todo` raises `NameError`/`AttributeError` | ✅ Fixed | `commands.py:160-162` |
| 3 | `_relationship_text` only shows first relation type | ✅ Fixed | `lib.py:377` — `return` dedented |
| 4 | `_list(..., ics=True)` skips filter on first object | ✅ Fixed | `lib.py:441` |
| 5 | Inverted condition in `interactive_split_task` — never postpones | ✅ Fixed | `interactive.py:336` |
| 6 | Year duration ~15 days (missing `*24`) | ✅ Fixed | `timespec.py` — corrected constant; `y` branch now uses `relativedelta` |
| 7 | `parse_add_dur` year branch crashes on `date` / Feb 29 | ✅ Fixed | `timespec.py` — `relativedelta(years=n)` handles both |
| 8 | Multi-unit duration loses all but last unit (no `dt`) | ✅ Fixed | `timespec.py` — accumulate `diff` instead of overwriting |
| 9 | Event-only guard in `add-time-tracking` never fires | ✅ Fixed | `cli.py:202` — fixed `all()` |
| 10 | `timeline_suggestion` crashes on all-day / DTEND-less events | ✅ Fixed | `panic_planning.py:112` |
| 11 | `interactive check-due --limit` is a string, not int | ✅ Fixed | `cli.py:519` — added `type=int` |
| 12 | `obj.icalendar_component_UID` crashes in inconsistency-log path | ✅ Fixed | `lib.py:355` |
| 13 | Leftover `breakpoint()` in `_procrastinate` | ⏸ On hold | `lib.py:241-244` |
| 14 | `time_tracking` string iterated char-by-char | ✅ Fixed | `lib.py:165` — wrap scalar in list |
| 15 | `dismiss-panic` double-prefixes lookahead (`++60d`) | ✅ Fixed | `cli.py:538` + `commands.py:466` |
| C1 | `_interactive_edit` duplicated in `commands.py` (stale copy) | ✅ Fixed | Deleted copy, import canonical from `interactive` |
| C2 | `pdb` hand-off block duplicated | ✅ Fixed | Extracted `_pdb_edit(obj)` in `interactive.py` |
| C3 | Inline summary fallback duplicates `_summary` | ✅ Fixed | `interactive.py:301` uses `_summary(obj)` |
| C4 | `get_obj` / `_get_obj_from_line` duplicate parsers | ✅ Fixed | Deleted `get_obj` closure, use `_get_obj_from_line` |
| C5 | Duration grammar encoded in 4 places | ✅ Fixed | `timespec.py` exports `DURATION_UNITS`/`DURATION_RE`/`DURATION_TOKEN_RE`/`is_duration`; all 4 sites use them |
| C6 | Component-type detection by raw-string sniffing | ✅ Fixed | `lib.py` exports `_component_type`/`_caldav_objclass`; all object/raw sites use them |
| C7 | `category` vs `categories` special-cased in 5 places | ✅ Fixed | `lib.COMMA_LIST_ATTRS` registry + helpers; edit path centralised; also generalised to `resources` and added `--add-categories`/`--add-resource`/`--add-resources`; `--set-category` deprecated. Select-by `--category`(substring)/`--categories`(exact) left intact (caldav search semantics) |
| C8 | `interactive_config` key list hardcoded / diverged | ✅ Fixed | Was also dead code (orphaned since the argparse→click migration). Re-wired as `plann configure`; connection prompt keys derived from `caldav.config.CONNKEYS` (asserts no drift); fixed `ssl_verify_cert`→`caldav_ssl_verify_cert`, added `features`/`calendar_name`/`extra_config.time_tracking`, dropped never-read `language`/`timezone` |
| C9 | `extra_config` smuggled as monkey-patched attribute | ❌ TODO | Cleanup |
| C10 | `_editor` re-implements `shutil.which` | ✅ Fixed | `interactive.py` — uses `shutil.which`, raises clear error if no editor found |
| C11 | `_split_vcals` hand-rolls VCALENDAR parsing | ✅ Fixed | Now `icalendar.Calendar.from_ical(ical, multiple=True)`; handles CRLF (the LF-only scanner returned nothing on CRLF input). Tests added |
| E1 | `find_calendars()` called unconditionally (even `--help`) | ✅ Fixed | Discovery deferred via `_LazyCalendars` wrapper; `plann <subcommand> --help` no longer connects |
| E2 | `Template(skey)` rebuilt on every sort comparison | ✅ Fixed | Sort-key logic extracted to `_sort_key_function`; template compiled once per key. Tests added |
| E3 | `_relships_by_type` N×R round-trips in `list --top-down` | ❌ TODO | Efficiency |
| E4 | `_set_task_attribs` issues a fresh server `_select` per attribute | ❌ TODO | Efficiency |
| E5 | `--uid` resolution keeps querying after a hit | ❌ TODO | Efficiency |
| D1 | `raise NotImplementedError` unreachable at `timespec.py:229` | ✅ Fixed | Removed unreachable statement |
| D2 | `'with family'` checked twice in `command_edit` | ✅ Fixed | `interactive.py` — second check now `'with parent'` → `with_parent` |
