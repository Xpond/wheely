# The files browser

A keyboard-driven directory browser, reached by typing `files` into the wheel.

Two columns on one card: the directory on the left, what the selection *is* on
the right.

It answers where is it, what is in it, and open it — and then the things you
reach for once you are already looking at the file: edit it
([`Ctrl+E`](#editing)), move or copy it, [rename](#moving-files) it, [make
one](#moving-files) beside it, copy its path, throw it away. Each earns its place
the same way: you are looking at the thing, and acting on it should not cost you
a terminal.

Every one that writes can cost you data when it is wrong, so none of them are
quiet. Nothing is overwritten, a delete goes to the trash and is asked twice in
red, and a save is confirmed by reading the file back.

## Keys

| | |
|---|---|
| type anything | filter the current directory by name |
| `/` or `~` | switch the field to a path from here or from home — see [Path entry](#path-entry) |
| `↑` `↓` `Tab` `Shift+Tab` `Ctrl+N` `Ctrl+P` | move the selection, wrapping at both ends |
| `Space` | play/pause a video preview |
| `Shift+Space` | type a space in the filter while a video is selected |
| `Enter` | descend into a folder, or hand a file to the app that owns it, text to your editor |
| `→` | descend into a folder; on a file it does nothing |
| `←` | go up one directory, landing on the folder you left |
| `Backspace` | delete a character, then go up one directory, then back to the wheel |
| `Home` `End` | the first and last row |
| `PageUp` `PageDown` | a page of rows, one kept for orientation |
| `Shift+↑` `Shift+↓` | scroll the preview three lines |
| `Shift+PageUp` `Shift+PageDown` | scroll the preview a page |
| `Shift+←` `Shift+→` | pan the preview sideways, for lines past the edge |
| `Shift+Home` `Shift+End` | the top and the bottom of the preview |
| `Ctrl+E` | edit the previewed file — see [Editing](#editing) |
| `Ctrl+X` `Ctrl+C` | take the selection to move or to copy — see [Moving files](#moving-files) |
| `Ctrl+V` | place it in the directory you are standing in |
| `F2` | rename the selection — see [Moving files](#moving-files) |
| `Ctrl+Shift+N` | make a file or a folder here — the name says which, see [Moving files](#moving-files) |
| `Del` | trash the selection, asked twice |
| `Ctrl+Y` | copy the selection's path to the clipboard |
| `Ctrl+Enter` | open a terminal in the directory you are in |
| `Ctrl+O` | order by name, then newest, then largest — see [Ordering](#ordering) |
| `Ctrl+H` | show hidden files |
| `Ctrl+U` | clear the field |
| `Ctrl+W` `Ctrl+Backspace` | back one word of the filter, or one segment of a typed path |
| `Ctrl+T` | pop out into a window, and back — see [Popping out](#popping-out) |
| `Ctrl+B` | slide the list out so the preview takes its width, and back |
| `Ctrl+D` | show a changed file's diff instead of its contents, and back — see [Uncommitted changes](#uncommitted-changes) |
| `F1` | show every key in the legend, or only the everyday ones |
| `Esc` | clear the field, then close |

Shift is the one modifier that means "the other pane", and while the list is
shown it is the whole rule: every bare key drives the list, every shifted one
drives the preview.
`Home` is the first row rather than the home directory, because `~` already
opens path entry sitting there and is the character that says so.

`Ctrl+B` slides the list out to the left and the preview takes the width. With
the list hidden the preview is the view, so the bare keys act as shifted ones —
`↑` `↓`, the page keys and `Home` `End` scroll it — and `←`, or `Backspace` with
nothing left to delete, brings the list back rather than going up. The preview slides along at its old width and widens only
once the list is out: reflowing a Markdown table every frame of the slide would
stutter. The choice holds across the overlay and its windows while the shell runs.

The mouse works too — hover only tints a row, a click selects it, a double click
opens it, a click outside the card closes it, and the wheel scrolls whichever
pane is under the pointer. In a folder's preview, the entry under the pointer is
tinted too; a click on it enters the folder with that entry selected, and a
double click opens it. The click area lies over the whole preview, so the second
click counts whatever the preview shows by then; dragging no longer scrolls the
preview, the wheel and `Shift`+arrows do.

## Home is the floor

The browser opens at `$HOME` every time and cannot be navigated above it, or
above the folders the wheel searches outside home (`folders` in
`~/.config/omarchy/wheel.json`), so the wheel's results there open here too.
A typed `..` is collapsed before that check; a symlink inside home that points
outside is still followed. Anything resolving outside those roots
resolves *to* home rather than being refused, so going up from a searched folder
lands at home. There is no state the panel can be left holding that it cannot
get out of.

Each root outside home is listed at home as a folder named by its full path
(`/mnt`), so it is a walk away and a held copy or move can be carried there;
going up from it lands back on its row. The row stands for the root itself, so
it cannot be held, renamed or trashed.

It does not remember where you were. A remembered directory is only valid until
something moves, renames, unmounts or deletes it, and then the panel opens onto
a path that no longer exists and shows an empty list with no hint of why. Home
is the one directory that is always there. A caller passes
`{"dir": "...", "select": "..."}` instead, which is how the wheel hands a file
over: the browser opens where the file lives with the file selected, so its
preview is up before you have touched a key.

## Path entry

A leading `/` or `~` turns the field from a name filter into a path. The
directory being listed becomes whatever complete directory you have typed so
far, and the tail you are still typing filters it — so the list *completes* the
path as you write it, and `Enter` descends into what it found.

`~` starts from home. `/` starts from the folder you are in: typed in
`~/projects/notes/docs` it writes `/projects/notes/docs/` into the
field, so the list stays put, `Ctrl+W` climbs a segment and typing goes deeper.
Both are rooted at `$HOME`, so `/projects/notes` and
`~/projects/notes` are the same path; outside home, `/` starts from home.

**A typed path is written into the trail, not beside it.** The breadcrumb
already *is* the directory being listed, so the tail still being typed is drawn
as the next segment of it — accent-coloured, with the caret at its end — and the
filter chip stays behind for plain name filters. Showing both put the whole path
on the header twice, once walked and once typed, and two spellings of the same
place read as two places. The count reads off the same tail (`root.query`), so
`/Projects/` says `10 items` rather than `10 of 10`.

## Ordering

Folders first and then alphabetically, until `Ctrl+O` asks for something else:
**newest** first, then **largest** first, then back to name. The header says
which one you are in, and the order stays with the panel — it is a way of looking, not a place, so unlike
a remembered directory it cannot go stale.

Where the filter landed only ranks under **name**: once you have asked for
newest first, a prefix match jumping the queue is the sort lying about itself.
Folders are never ordered by size, which for a directory counts the block its
entries are listed in rather than anything inside it.

## The two columns

Both columns are sized in **characters of the font they render**, not in
fractions of the display:

    listWidth     28 characters + icon + row padding
    previewWidth  100 characters
    card width    the sum of those, plus gaps, capped at 92% of the screen

A percentage-based split gives the preview a wider box than any line of code
will fill, and the void on its right is width nobody asked for. A name is about
so many letters long and a line of code is about so many columns wide; those
are the units, so those are what the layout is written in. `TextMetrics`
measures the real advance width of the real font, so this holds under any
`[font] size` or family the theme sets.

The card carries **one ground colour**. The two columns are told apart by the
space between them and the rule under their headings — not by a second fill or
a second frame, which turn a card into two cards and make the preview look like
a window dropped inside this one.

The header is one line: the path as a breadcrumb trail with the leaf at full
strength and the trail behind it dimmed, then whatever is narrowing the list,
then the count, all flowing left. The preview's own heading — name, size, the
pixel dimensions if it is an image or the line count if it is text, date —
right-aligns on the same line. The
count sits with the path rather than at the far edge because right-aligned it
stacked directly above the preview's size and date, and two dim figures in a
column read as two facts about one file.

The foot of the card carries the keys, centred, in key-and-word pairs: the key
lit, the verb whispered. A hairline above it makes the row a band rather than
text floating in the padding.

## The preview

Previews follow the selection:

| selection | shown as |
|---|---|
| a folder | its contents as a listing — name, size, date — capped at 400 entries |
| an image | itself, aspect-fit, async, formats Qt actually has plugins for |
| a video | muted video preview with play/pause, seeking, time, volume and mute |
| a `.md` file | rendered Markdown — headings, bold, code blocks |
| any other text | syntax highlighted, with line numbers |
| anything else | its size and `no preview` |

The previews are read-only renderings. `Ctrl+E` replaces a text preview with the
file itself — see [Editing](#editing).

Video previews use Qt Multimedia's FFmpeg backend (`qt6-multimedia`,
`qt6-multimedia-ffmpeg`). Each video plays muted as soon as it is selected;
click it or press `Space` to pause. The fullsize button opens native mpv
fullscreen at the current position. Leaving a video releases its player.

Previews decode in software: Qt picks hardware decoding even for codecs the GPU
lacks (AV1 on older cards) and shows black. An `Env` pragma in the shell's
`shell.qml` sets `QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,` (an empty device list), so
no other Qt app decodes this way.

The preview follows the selection only once it has **stopped moving** — 60 ms,
the same wait the highlighter takes — so held-down arrows do not read and lay
out every file they pass over.

Files over **256 KiB** are never read. A file that grew past that since it was
listed is loaded off the UI thread but never decoded on it: 200 MB blocked the
shell for seconds. A NUL byte in the first kilobyte is what
marks a binary, rather than an extension list to maintain: `.frag` and `.qsb`
sit either side of any list you would write by hand, and the bytes do not lie.

Arriving from the wheel while an edit is unsaved does not move: the browser
stays on the file and asks you to save or discard it first.

## Uncommitted changes

Inside a git repository the list marks what changed since the last commit:
git's own letter on a file — `M` modified, `A` added, `D` deleted, `?`
untracked — and a dot on a folder with changes anywhere under it, so changes
can be followed down from the root. A folder git does not track at all is `?`
as a whole and its preview is unmarked; inside it, each entry has its own mark.
A folder's preview carries the same marks between each name and its size. The
preview is one plain text per column, and a plain text takes one colour, so the
marks are a second text laid over room the rows keep for them, placed past the
row's glyph by its measured width. A changed file's heading leads with how many
lines it adds and removes, `+11 −2  ·  name`, set off by the same dot as the
facts after the name.

Deleted files remain in the list as read-only rows, below everything that
exists: they arrive with git's status, which is read once the folder's rows are
in, and so move no selection already made. Missing parent folders remain
navigable too. Backing out of one selects nothing until its row arrives and
then lands on it, rather than resting on the top row first; a key or a click
meanwhile wins. Enter on a deleted file shows its diff. These rows cannot be
edited, renamed, copied, moved, or trashed.

`Ctrl+D` shows a changed file's diff in place of its contents — staged and
unstaged, against `HEAD`, coloured in the highlighter's One Dark. git's header
goes, since the heading names the file, and each `@@` becomes a `⋯` break
carrying git's context. git lists a block of removed lines before the lines
that replaced them; instead each old line sits above the most alike new line,
in order, with what changed in bold. A change inside a word bolds the whole
word, one at a word's edge only itself; past ASCII every character counts as a
word's, so bold never splits an emoji, its skin tone or an accent. A line
without its last newline ends in a circle-slash, Nerd Font's octicon at U+F468,
for git's `\ No newline at end of file`: a save that only adds the newline
shows that mark rather than two identical lines. The mark counts for nothing
when lines are compared, so even a lone `}` pairs. Lines sharing under half
their length at their two ends are not alike, and stay plain removals and
additions. Pairing has a fixed work budget; larger blocks keep Git's unified
order with every line intact, so selecting a heavily rewritten file cannot
stall on pairing. The gutter numbers lines as the file now has them, so a
removed line has none. Unchanged files and images keep their usual preview, so
the arrows can walk the list with the diff on. A changed file's preview waits
blank for its diff rather than flash the file, which loads first; an empty diff
gives it back. The choice holds while the shell runs, and while it is on,
`ctrl+d hide diff` is lit in the legend: the browser reopens in the diff, and
an unexplained diff looks like a broken file. `Ctrl+E` edits the file, never
the diff.

Untracked files and files in repositories without a first commit compare
against an empty file. A small diff remains readable even when the current
file exceeds the normal 256 KiB content-preview limit.

## Moving files

`Ctrl+X` or `Ctrl+C` takes the selected entry, you walk to another directory,
`Ctrl+V` places it. `F2` renames it where it stands, `Del` puts it in the trash.
The foot names what is held and what `Ctrl+V` would do with it; the heading says
what happened. A move spends its source and the hold is released; a copy keeps
it, so it can be placed again somewhere else.

**Rename types into the filter chip**, which is already a text box with a caret
in it, sitting where the name reads — so a rename needs no second field, only a
different fill, so it cannot be mistaken for a filter narrowing the list. A name
with a `/` in it is refused: that is a move being asked for in the wrong field,
and moving is what `Ctrl+X` is for.

It is a real field, not an append-only one: renaming is mostly changing a few
characters in the middle of a name you already have. `←` `→` `Home` `End` move
the caret, `Backspace` and `Del` cut either side of it, `Ctrl+U` and `Ctrl+K`
cut to the ends, `Ctrl+V` pastes with separators stripped. It opens with the
caret on the stem, before the extension. The chip draws the name in two halves
with the caret between them, so it stands where the next character will go; a
filter is only ever typed at, so its caret is always the trailing one.

**Delete trashes, and asks twice, loudly.** `gio trash` puts the entry in the
freedesktop trash with its original path recorded, so it can be got back — the
difference between a delete you can survive and one you cannot. It is still
asked twice, because it is the one verb here that takes something away.

The question is asked where you are looking: the row itself fills with a fixed
red and the foot turns red and reads `del  again to trash <name>`. Any key that
is not the second `Del` cancels it, so does moving the selection, and so does
waiting three seconds — a second
`Del` can never land on a row you did not aim it at.

**Nothing is ever overwritten.** The destination name is tested before the
command runs:

    sh -c 'if [ -e "$2" ] || [ -L "$2" ]; then exit 17; fi; exec mv -- "$1" "$2"' files <src> <dst>

Paths go as arguments, never spliced into the script, so a name with a space, a
dash or a `$` in it is just a name. `17` is this panel's word for *something is
already called that* and is nothing `mv` or `cp` returns on their own; it comes
back as `a wheel.md is already here` rather than being resolved by inventing a
`(copy)` name — a file manager that renames your file for you is one you cannot
predict. Directories go with `cp -r`, and `mv` refuses to move one into itself
without any help from here.

**`Ctrl+Shift+N` makes one**, into the same chip a rename types into.

**The name says which of the two it is.** A dot in it is an extension, and an
extension is what a file has — which is how the listing above reads them back
anyway, so there is nothing extra to remember. A trailing mark overrides that
either way, and neither mark can be part of a name in the first place:

    archive         a folder        v1.2/       a folder
    notes.md        a file          Makefile.   a file
    .gitignore      a file          .config/    a folder

A second binding for the second verb would have been a second thing to learn for
a difference the name already spells out. Anything *else* with a `/` in it is
still refused: a slash in the middle is a nested path being asked for in a field
that names one thing.

`mkdir` and `touch` go out through the same script with the verb as an argument,
so both cross the same collision test and come back as the same `17`.

**`Ctrl+Y` copies the selection's path**, through `wl-copy` with the path as an
argument rather than spliced into the script — the discipline the move commands
are written with.

## Editing

`Ctrl+E` turns the preview into a `TextEdit` over the same file, `Ctrl+S`
writes it, `Esc` comes back.

| | |
|---|---|
| `Ctrl+E` | edit the previewed file |
| `Ctrl+S` | save |
| `Ctrl+C` `Ctrl+X` `Ctrl+V` `Ctrl+A` | copy, cut, paste, select all |
| `Esc` | back — pressed twice, within 2 s, if there are unsaved changes |

What makes it safe rather than merely possible:

**It is modal, because the keyboard is a filter.** Every printable key in this
panel lands in the search field; nothing can type into a file and into a search
box at once. While `editing`, the whole keyboard goes to the editor and only the
edit verbs are kept. Clicks and the click-outside shield stop moving the
selection for the same reason.

**It edits plain source, not the rendering.** What the preview draws is pygments
markup or Qt's Markdown; editing a rendering saves the rendering — `<font
color="#C678DD">def</font>` into your Python file. So the colour drops away for the
length of the edit, which is also the clearest signal that you are looking at
bytes rather than at a picture of them. The heading says `editing`, `unsaved`,
`saved` or `write failed` while it lasts.

**It edits only what it can write back whole.** `FileView` holds `fullText` —
the file as it is on disk — and the editor takes all of it, never the preview's
lines, so a file of any length edits. A file over 256 KiB, binary, or not valid
UTF-8 is not editable -- the bytes are what get checked, so a file that
genuinely contains U+FFFD still edits. Nor is one holding CR line endings or
no-break spaces, which Qt's editor turns into LF and spaces, or a BOM, which
`FileView` drops. Writes go out `atomicWrites`.
A save is then confirmed by reading the file back, because `FileView` will not
tell you (see [Traps](dev/files.md#traps)), and `endLine()` adds the trailing newline `vim`
would, since a file saved without one is a file `git` calls damaged.

Closing is refused while there are unsaved changes — `close()` routes to
`leaveEdit()` instead, so a click outside arms the discard rather than throwing
the edit away silently.

### Syntax highlighting

Colour comes from **pygments**, not from a tokeniser written here. One process
per settled selection buys every language it knows, correctly, against a
hand-rolled pass that would get shell quoting wrong on its first day.

Colour is a nicety, not a dependency. If `python3` or pygments is missing the
process yields nothing and the escaped plain text stays on screen.

### Markdown

Rendered rather than dumped — line numbers and a no-wrap column are right for
code and wrong for prose. Links show as their words, since the pane cannot follow
them, and blank lines keep the paragraphs apart.

## Popping out

`Ctrl+T` moves the browser out of the overlay into a normal Hyprland window,
keeping the folder, the selection and the preview. Hyprland tiles it beside
whatever else is open, and it moves, floats and pins like any other window. The
overlay goes, and the dimmed backdrop with it; the window is nearly solid, so the
blurred backdrop barely shows through. `Ctrl+T` in the window brings the overlay
back the same way.

To the shell the browser is then closed, so opening the wheel or a panel leaves
the window alone, and `SUPER+W` closes it as it closes any window. `Esc` only
clears the field: closing is the window's business. A file picked in the wheel
sends the window there and focuses it; summoning the browser without a path only
focuses it. Once the window is gone, the next summon opens the overlay again.

A file picked in the pinned search (see [`wheel.md`](wheel.md#pinning)) opens the
browser inside the search's window rather than a window of its own. There `Esc`,
or `Backspace` at home, goes back to the search, and `Ctrl+T` moves the browser
to the overlay, leaving the search in its window.

Closing a window cannot ask twice, so an unsaved edit does not go with it: the
overlay comes back holding the edit, where `Esc` asks as usual.

## Known limits

- **Colour lands a beat after the text.** Debounce plus interpreter start on
  every selection. Caching the last few results, or keeping one Python process alive to serve
  requests, would be the next step.
- Markdown is rendered by Qt, and Qt's importer is lossy: an indented code block
  keeps its indentation but not its distinction from surrounding prose, and a
  table's cells arrive with nothing between them, so a row reads as one run-on
  word. Tables are the worst thing this preview renders.
- The line-number gutter counts the lines of the *source*. A wrapped Markdown
  paragraph has no numbers at all, by design; a code file never wraps, so the
  two agree.
- No undo for a move, a copy, a rename or a new file — only a delete can be
  taken back, out of the trash. Use `yazi` for the rest.
- A key legend of more than ten keys takes two lines. Where the card or the
  window is narrower than a line, it shrinks to fit.
- An image's pixel size comes from `identify`. Colour and dimensions are both
  niceties rather than dependencies: without ImageMagick there are no numbers,
  and the size and the date still stand.

How it is built, its traps and what the tests check: [`dev/files.md`](dev/files.md).
