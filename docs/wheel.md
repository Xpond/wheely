# The wheel

A radial launcher for Omarchy, on `SUPER+A` or a key you choose (see **Settings**).

Your bar's panels sit on a ring, reachable by direction; typing turns the hub
into a search over every entry in the Omarchy menu, every installed app, every
open window, every theme and font, keybindings, settings, files (after `/`) and
the manual. It replaces reaching for a handful of
separate `SUPER+CTRL` shortcuts with one key and a direction.

The ring is for things that have a widget. Everything else in the menu —
Install, Remove, Update and the rest — is one search away instead of one more
disc, because a ring you have to read is slower than a word you can type.

Hold an arrow key for a few seconds and the wheel spins up a scene of its own,
described in [the internals](dev/wheel.md#the-comet).

## Keys

| | |
|---|---|
| `SUPER+A` | open (tap — do not hold, see below); again to close |
| `↑` `↓` `←` `→` | `↑`/`↓` jump to the slice at that compass point; `←`/`→` step around the ring |
| `Tab` `Shift+Tab` | step around the ring; while searching, step the result list |
| `Enter` | fire the highlighted slice, or open it if it is a submenu |
| `↑` `↓` `Ctrl+P` `Ctrl+N` | step the result list while searching |
| `Ctrl+Home` `Ctrl+End` | the first and last result, from wherever you are |
| type anything | search menu entries, apps, windows, themes and fonts |
| `Backspace` | delete the character before the caret, then go back to the ring you came from |
| `Del` | delete the character after the caret |
| `Ctrl+W` `Ctrl+Backspace` | delete the word before the caret |
| `←` `→` | move the caret through the query; with `Ctrl`, a word at a time |
| `Home` `End` | the start and the end of the query; `Ctrl+E` also goes to the end |
| `Shift+←` `Shift+→` | select; with `Ctrl`, a word at a time |
| `Shift+Home` `Shift+End` | select to the start, or to the end |
| `Ctrl+A` | select the whole query |
| `Ctrl+U` `Ctrl+K` | delete to the start, or to the end |
| `Ctrl+V` | paste at the caret or over the selection, runs of whitespace collapsed to one space |
| `Ctrl+Y` | copy the highlighted path and close |
| `Ctrl+Enter` | open a terminal in the highlighted path's folder; on any other row, as `Enter` |
| `Ctrl+T` | pin the search as a window, and back — see [Pinning](#pinning) |
| `Esc` | clear the query, then go back to the ring you came from, then close |
| `SUPER+W` | close the wheel and whatever it opened |

The query is a Qt `TextInput`, which types, deletes, moves and selects on its
own; `MenuKeys.js` sees every key before it does.

Until you type, the field reads `Search · / files · = calc`, and a lone `/`
lists the files you have picked or, until there are any, names the two keys a
path answers to, `Ctrl+Y` and `Ctrl+Enter`.

`Backspace` inside a panel the wheel opened closes it and brings the wheel
back. A panel cannot tell the wheel from its own bar button, so it does not
try: it calls `xpo.wheel back`, and the wheel returns `none` for a panel it did
not open. The panel takes the key either way, so in a panel the wheel did not open
Backspace does nothing.
Switching between bar panels with Tab or Ctrl+←/→ carries that return to the
next panel, so Backspace still brings the wheel back.

Mouse works too: the whole screen is a compass around center, so a flick in
any direction selects that slice. Releasing the key commits it. The scroll
wheel steps the ring one slice per notch, or the result list while searching.

Clicking the field or the result stack does nothing, rather than closing the
wheel: everywhere else a click away closes it, and the two surfaces you are
most likely to hit by accident -- the thing shaped like a text field, and the
gap beside a row you missed -- must not count as "away". Neither is clickable
in any other sense, and neither shows a hover state, because there is nothing
to click for: the field always holds the keyboard, so a click can do nothing a
keystroke does not already do. The rows themselves are the exception: hovering
one selects it and a click runs it, as on the ring.

## Pinning

`Ctrl+T` moves the search out of the overlay into a normal Hyprland window,
keeping the query. Only the field and its results go: no ring, sky or fades.
The field sits centered, as on the wheel, and the results show as many rows as
fit below it, up to eight. The window's ground is the backdrop's tint, which
Hyprland blurs as it blurs the backdrop, so the empty space follows the
wallpaper; the field and rows are a little more translucent than on the wheel
and keep their shadows.

A pick runs at once and the window stays, cleared for the next. A panel opens
over it as it would from the bar, and gives the keyboard back when it closes. A
file opens Files inside the same window; `Esc`, or `Backspace` at home, goes
back to the search. `SUPER+A` focuses the window instead of opening the wheel,
`Ctrl+T` in it brings the wheel back holding the query, and `SUPER+W` closes it
like any window. Each new `/` search scans again, as each open of the wheel
does, so files made after pinning are found.

## Search

**Every entry in the menu is a row.** Entries with an `action` run it. Entries
without one are submenus, and they are rows too — searching `install` has to
find Install, not only the things filed under it; picking one turns the ring
into its children, `Backspace` goes back up, and the hub prints where you are.
That is the only reason the ring drills at all; the default ring has no
submenus on it.

The exception is a `provider`, whose rows the menu generates at runtime — the
app list, the installed fonts. The wheel cannot render those, so a provider row
hands the whole route to `omarchy-menu summon <id>` rather than being dropped.
That also covers any provider a later Omarchy adds that `MenuIndex.js` has
never heard of.

`when:` and `checked:` are evaluated on every open, as Omarchy's own menu
re-checks its rows on every open, so a row follows state that changed under it:
Stop Screenrecording exists only while something records, and an Install row
turns into a Remove row once the package is in.

A `when` that fails hides the row, and a submenu whose children all failed is
hidden too, so a slice never drills into an empty ring. A `checked` that holds
appends ✓ to its row, on the ring and in search: the default browser,
terminal, editor and agent, the DNS, the update channel.

A submenu's slices run clockwise from north in menu order, except a ring made
only of Top, Right, Bottom and Left: it puts each where it points, so the bar
position menu matches the screen.

Open windows come from `Hyprland.toplevels`. Their rows say
`Workspace <n> · <app id>`; launcher rows say `App`, so focusing an existing
window and launching an app are distinct choices. The workspace is the
toplevel's live one, since the cached IPC object goes stale, and it is searchable: `workspace` lists every open window and
`workspace 2` the ones on 2 (the scratchpad reads `Workspace scratchpad`).

Themes and fonts are `omarchy theme list` and `omarchy font list`, re-read on
every open along with the current theme and font, which are marked ✓, and fired
back as `omarchy theme set '<name>'`. Each read takes a few milliseconds. Both
are otherwise buried: `style.theme` in the menu shells out to
`omarchy-theme-switcher`, a second overlay on top of the first. Lock-screen
designs come from `omarchy-lock-design list`, re-read the same way, but join
the menu as one Style › Lockscreen Designs submenu: search finds that entry,
and the designs, marked `search: false`, show only inside it. Picking one runs
`omarchy-lock-design set`, and each carries a `checked:` against
`omarchy-lock-design current`, so the chosen one's ✓ comes back with the rest.

A binding that runs what a row already runs — the row's command, its panel's
toggle, or Omarchy's menu opened at it by id or alias — is not a second row. It
lends that row its description as search words, so `idle` finds Stay Awake
(Toggle locking on idle) and `ocr` finds Capture › Text. Bindings sharing a
command are one row. The wheel's own bindings (open, commit, close) are no rows, since
they mean nothing from inside it. The keys themselves are never shown: the wheel is
there so that none need remembering.

A window action — Toggle floating, Full screen, Move window to workspace 3 —
acts on Hyprland's active window, and while the wheel holds the keyboard
`Hyprland.activeToplevel` reads null. Hyprland's own active window stays put,
though (`hyprctl activewindow` still names the window behind the wheel), so the
action lands whatever the timing.

When rows refresh, selection follows the same action to its new position. If that
action disappears or its command changes, selection clears. A refresh cannot turn
a selected Logout into Reboot. A new search query still selects its first result.

App and window text accepts substrings: `calc` finds `Omacalc (Development)` even
without calculator keywords. Other rows still require each query term to start a
word, keeping menu searches narrow. Rows then
sort on six keys: **rank** (label-prefix, then a label word, then a hit
anywhere else — breadcrumb, alias, app id), **uses** (among equal matches,
the most picked first), **kind** (slice, window, app, theme/font, menu,
keybinding), an **exact label** (so "lock" puts Lock before
Lockscreen Designs until the designs are picked more), **recency**, and
finally **label length**, which floats
"Screenshot" over "Stop Screenrecording".

`search()` sorts its matches. File mode has too many to sort: it buckets them
by rank and name length as it scans, keeping only the first 40 of each tie,
which is every row that could be read. A file opened from the wheel before
leads its rank, most opened first, but never climbs into a better one, and a
bare `/` lists those files, latest first. Home and the folders added outside it
scan apart, in batches (`scan.py`), and a background worker ranks each batch as it
arrives, keeping home's ties ahead of added folders, so results show before
either walk finishes. Typing replaces the pending query; previous rows stay
clickable, and keyboard actions wait for the current query's results. Closing
cancels both scans and releases the worker's index. `Enter` on a path
opens the browser there, whether or not the browser was already up. The browser
keeps to home and the searched folders (Settings), so any other path opens the
way the browser opens a file, through `omarchy-open-path`.

An open window whose words match is never a weak hit: it counts as rank 0. A
window's title is written by the program, so a query lands mid-string
("…Omarchy Plugins - Brave") where a menu label has it at the front — without
this the window you are looking at sorts below seven rows offering to install
the thing. A term found only inside a word ranks a window like any other row, or
`ar` would put a terminal titled `~/code/omarchy-notes` above Arch.

Recency orders the windows among themselves, most recently focused first, and
is inert for every other row.

A leading `=` turns search into a calculator, `Calc.js`: `+ - * / ^` and
parentheses, with `^` binding tighter than a leading minus, as on paper
(`=-2^2` is -4). The answer shows fifteen significant digits, which also hides
float noise (`=0.1+0.2` is 0.3), centered under the query with a copy mark at
the row's end, and `Enter` copies exactly that and closes. Even the longest
answer, 23 characters, fits at the stock font size; anything wider is cut on
the left, as the query is. A half-typed sum, a unit or a letter shows "No
answer" rather than a guess; units and currency would need `qalc`, which
Omarchy does not ship.

## Manual

`manual.md` is the user's manual, and its table rows are search rows: `help`
lists them, led by **Wheely manual**, and a word finds the key for a task,
`help rename` the Files row for `F2`. Each row ends in its key and section.
The rows have no key of their own, so they are never counted or pinned.

Enter on any of them shows the whole manual on one sheet (`WheelManual.qml`):
one panel holding a card per section, a hairline between rows, keys drawn as
keycaps. It is drawn from the parsed rows, never the file, so nothing in the
plugin folder can be edited from it.

It is a cheat sheet, so it has to fit: a row is a few words on one line, and
keys any text field has are one "text keys" row, as Shift with the move keys is
one row in Files. At its own text size, larger than the shell's and never shrunk,
it fills one 1080p screen. Its columns, up to three, take most of the screen's
width, so the panel keeps clear of the edges; a smaller screen scrolls it with
`↑` `↓`, the page keys or the mouse wheel. `Ctrl+T` pins it in the search's
window, where it reflows the same way; `Ctrl+T` again brings it back.

The search field moves into the manual header and starts on an empty query,
so typing fades every row search would not find. `Esc`, or `Backspace` with an
empty filter, restores the query and results. Normal text editing works;
actions on the hidden results stay disabled.

## Settings

Settings are search rows: `wheely settings` lists them. Each row ends in its
value, and Enter changes it without closing the wheel.

**Wheely shortcut** (`SUPER + A`): Enter, then press a combo that includes
SUPER, since Hyprland takes a bound combo from every app and apps leave SUPER
alone. Hyprland's bindings pause while the row records, so a taken combo can be
chosen; the row says what it would replace. Enter saves; Esc or bare Backspace
cancels. Saved to `~/.config/omarchy/wheel-shortcut`, then Hyprland reloads.
Pressing the shortcut with the wheel up closes it.

**Wallpaper pause** (`CTRL + SPACE`), while Wheelie or Tidal is installed: the
key that pauses and resumes the active theme's scene, recorded the same way. It is bound only
while one of them is the active theme; otherwise apps keep it. SUPER is optional
here, as the default shows, but the combo needs CTRL, ALT or SUPER, and the
wheel's own keys are refused. Saved to
`~/.config/omarchy/wallpaper-pause-shortcut`, then Hyprland reloads.

**Wheely ring** (`Bar` or `Custom`): Enter edits the ring (The ring).

**Backdrop**: Enter, then ←/→ change how much the backdrop hides the desktop,
in tenths, saved as you go; Enter, Esc or Backspace is done. 0% is a clear
desktop with no blur (`~/.config/omarchy/wheel-blur`). The dim is
`[menu] scrim-alpha` in `~/.config/omarchy/shell.toml`, which Omarchy's own menus use too.

**Centered panels** (`On`): Enter toggles. Off, bar panels open beside their
widget with no backdrop (`[wheely] panels = native` in `shell.toml`).

**Searched folders** and **Skipped folders** change what `/` searches. By
default: home, hidden files included, six levels deep, skipping every
`.cache`, `.git`, `node_modules`, `.ssh`, `.gnupg` and `.password-store`, and
whatever a git repository's `.gitignore` lists. Enter lists the entries. Type to find one to add and Enter
adds it: Searched takes a path from `/` outside home; Skipped offers folder
names first, each skipping every folder called that, anywhere, as the defaults
do, then single folders under home. Del removes; Esc or Backspace on an empty
query is done. An emptied list is its default again. Files found in an added
folder open in the browser, like those under home. Both lists live in
`~/.config/omarchy/wheel.json` as `"folders"` and `"skipped"`.

**Wheely history** (`history`): your picks, newest first, files included.
Enter runs one; typing goes back to search; Esc or Backspace is done.

**Forget picks** ends in how many are remembered. Enter, then Enter again
clears them; Esc or Backspace keeps them.

## What it remembers

Every pick is counted, keyed by `MenuIndex.keyOf` -- a panel's plugin id, a
menu entry's dotted id, `app:` plus a desktop id, or a theme/font or
keybinding command, so a binding keeps its count when its keys change, or
`file:` plus a path -- and the count sorts right under how well a row matches.
So `loc` puts a picked Lock over a never-picked LocalSend, while `br` keeps
Files, which matches only through its "browser" keyword, under every row whose
name starts with `br`, however often Files is picked.

Windows are deliberately uncounted -- their address is new on every launch, so
counting them would grow the file without bound, and they already sort on live
focus order. Opening a setting row is no pick either.

The counts live in `~/.local/state/omarchy/wheel-uses.json`, written through on
each pick rather than batched at exit -- the wheel is a plugin in a shell that
gets restarted, so no orderly shutdown is guaranteed to arrive. The **Forget
picks** setting empties it. There is no decay: what you
reach for through a wheel is stable for months, and a half-life is a second knob
to be wrong about.

## The ring

By default the ring is the panels your bar carries — written as a bare id or as
an object with an `id`, as Omarchy reads either — in a fixed order, plus the
clipboard overlay — which is not a bar widget, so nothing in the bar vouches
for it. Adding a widget to the bar adds it to the wheel; the wheel is not a
second list to keep in sync with the first. A machine that has never edited its
bar has no user config, so the layout Omarchy ships
(`$OMARCHY_PATH/config/omarchy/shell.json`) is read instead — otherwise the
ring would offer panels that machine has no widget for.

Search does not follow the ring. Each open asks the shell's facade for every
bar widget the live bar can open and every enabled third-party panel or
overlay — Weather, clones, plugins such as Omastorm — so a panel is searchable
whether or not it has a disc. Omarchy's own panels come through its menu.
Clones borrow their source's mark, Weather uses its widget's own glyph, and
unknown panels a generic one.

To choose the ring yourself, open the **Wheely ring** setting: the ring becomes
its own editor, starting from the ring you have. Type to find anything, and Enter
adds it after the selected slice, or last when none is. Del removes the selected
slice, Shift+←/→ swaps it with its neighbour, across north too, and Esc is done.
Ctrl+R, pressed twice, resets the ring to the bar's widgets, as removing the
last slice does. Every change is saved as it is made, to
`~/.config/omarchy/wheel.json`:

```json
{
  "slices": [
    "omarchy.audio",
    "app:chromium",
    "omarchy.clipboard",
    "system",
    "trigger.capture"
  ]
}
```

A slice is the key its picks are counted under (What it remembers): a panel's
plugin id, a menu id from `omarchy-menu.jsonc`, `app:` and a desktop id, or a
theme, font or keybinding command. So the ring takes anything search finds,
Weather, clones and third-party panels included, but no window, file or answer,
whose key would not outlast it, and no setting. An app wears its own icon, as
in search; a menu id with an action runs it, and a submenu drills the ring into
it. A key that names nothing today, such as a menu entry whose condition is
false or a widget taken off the bar, is not drawn, but the editor keeps it in its
place, so it comes back when it names something again. The file is watched, so a hand edit shows as you save, but
the editor writes it back without comments, keeping any other keys.

The ring sizes itself to what it holds. It keeps a constant arc distance per
slice and grows its radius to pay for it, so a disc and its label have the same
room at fourteen slices as at eight. Growth stops before the labels would run
off the short edge of the screen, and only then do the discs shrink to fit the
chord between their neighbours.

## Known limits

- The pinned search has no ring: submenus and the ring editor need it, and
  recording a shortcut needs the overlay, so they work from the wheel only. Its
  results do not scroll with the mouse wheel.
- A window is found by its title or its app id, never by what is running
  inside it: a terminal holding a Claude Code session is titled after the
  session's topic, so `claude` will not find it. Searching the app id
  (`kitty`) lists every window of that app, most recent first.

How it is built, its traps and what the tests check: [`dev/wheel.md`](dev/wheel.md).
