# The files browser: internals

Maintainer notes for [the files browser](../files.md): the files, layout and rendering details,
traps, wiring, and what the tests check.

## Files

    plugins/xpo.files/
      manifest.json     kinds: ["overlay"], keepLoaded
      Files.qml         state, derivation, and both surfaces
      FilesOps.qml      everything that writes: one process, one contract
      FilesHeader.qml   breadcrumb, path entry, filter and rename field
      FilesList.qml     the directory, one row per entry
      FilesPreview.qml  the scroller, and the editor inside it
      FilesVideo.qml    muted video preview, controls and native mpv handoff
      FilesHints.qml    the foot: the legend, and what a held file would do
      FilesMenu.qml     context, keyboard and pointer state for the right-click menu
      FilesMenuCard.qml the main menu and submenu cards
      FilesActions.js   the menu as data: the rows an entry gets, and the commands they run
      FilesProcess.qml  a reader whose cancelled output never lands
      FilesIndex.js     snapshotting, filtering, path and text helpers
      FilesKeys.js      the key map: which verb a key means
      highlight.py      pygments colour for the preview
      git-preview.py    git status and diffs, for real or deleted paths

Each component takes the panel as `panel` rather than reaching for a parent, so
its one dependency is visible at the call site. `FilesPreview` owns its
scrolling and its editor and exposes verbs — `scrollBy`, `keepPlace`,
`scrollTo` — rather than letting the panel reach into a `Flickable`.

## The floor

**Home is the floor.** The browser opens at `$HOME` every time and cannot go above
it, or above the folders the wheel searches outside home (`folders` in
`~/.config/omarchy/wheel.json`), so the wheel's results there open here too.
Anything resolving outside those roots resolves *to* home rather than being refused,
so there is no state the panel can be left holding that it cannot get out of. Each
root outside home is listed at home as a folder named by its full path (`/mnt`); its
row stands for the root itself, so it cannot be held, renamed or trashed.

**It does not remember where you were.** A remembered directory is only valid until
something moves, renames, unmounts or deletes it, and then the panel opens onto a
path that no longer exists, an empty list with no hint of why. A caller passes
`{"dir": "...", "select": "..."}` instead, which is how the wheel hands a file over:
the browser opens where the file lives with the file selected.

`FilesIndex.within()` is applied on every path change — arrow navigation, `←`,
`Backspace`, and typed paths alike — after `cleanPath()` has collapsed `.` and `..`
segments, so a typed `..` cannot step over the jail; a symlink inside home that
points outside is not resolved, and is followed.

`within()` tests `root + "/"` rather than a bare prefix, because `/home/alex2` starts
with `/home/alex` and is not inside it. `display()` tildes only home
itself or a path under `home + "/"` for the same reason.

## Layout, preview and git status

**Both columns are sized in characters of the font they render**, not in fractions of
the display: the list 28 characters plus icon and padding, the preview 100, the card
their sum plus gaps, capped at 92% of the screen. A percentage split gives the preview
a wider box than any line of code fills. `TextMetrics` measures the real font, so this
holds under any `[font] size` or family the theme sets.

The card carries **one ground colour**; the columns are told apart by the space
between them and the rule under their headings, since a second fill or frame turns
one card into two. The header is one line: the breadcrumb (leaf at full strength,
trail dimmed), whatever narrows the list, then the count, flowing left, with the
preview's own heading right-aligned on the same line. The count sits with the path
because right-aligned it stacked above the preview's size and date and read as a fact
about the file. The foot carries the keys in key-and-word pairs, above a hairline.

**A typed path is written into the trail, not beside it.** With a leading `/` or `~`
the listed directory is whatever complete directory has been typed, and the tail
still being typed is drawn as the next breadcrumb segment, accent-coloured with the
caret at its end. Showing the trail and a path chip both put the same place on the
header twice. The count reads off the same tail (`root.query`). `/` starts from the
folder you are in; both forms are rooted at `$HOME`.

**Ordering** is folders first then names, or newest, or largest (`Ctrl+O`). Where the
filter landed ranks only under name, since under newest a prefix match jumping the
queue would be the sort lying. Folders are never ordered by size, which for a
directory counts its listing block rather than its contents. `ordered()` shuffles
before V4's `sort`, which slows badly on input already in another order, as
FolderListModel's code-point order is to `localeCompare`.

**Reading a file.** The preview follows the selection only once it has stopped moving
(60 ms), so held arrows do not read and lay out every file
they pass. Files over 256 KiB are never read; one that grew past that since listing
is loaded off the UI thread but never decoded on it (200 MB blocked the shell for
seconds). A NUL byte in the first kilobyte marks a binary, rather than an extension
list. Video previews decode in software: Qt picks hardware decoding even for codecs
the GPU lacks (AV1 on older cards) and shows black, so an `Env` pragma in the shell's
`shell.qml` sets `QT_FFMPEG_DECODING_HW_DEVICE_TYPES=,`.

**The diff view** (`Ctrl+D`) shows staged and unstaged changes against `HEAD` in the
highlighter's One Dark. git's header goes, each `@@` becomes a `⋯` break, and instead
of git's removed-block-then-added-block each old line sits above its most alike new
line, with what changed in bold (a whole word, or only the edge of one; past ASCII
every character counts as a word's, so bold never splits an emoji). A missing final
newline is a circle-slash (U+F468) that counts for nothing when lines are compared.
Lines sharing under half their length at their ends stay plain removals and additions,
and pairing has a fixed work budget past which git's order is kept. The gutter numbers
lines as the file now has them. A changed file's preview waits blank for its diff
rather than flash the file. The choice holds while the shell runs and is lit in the
legend, since the browser reopens in it and an unexplained diff looks like a broken
file. Untracked files and repositories without a first commit compare against an
empty file; a small diff stays readable past the 256 KiB limit.

The git marks in a folder's preview are a second text laid over room the rows keep
for them, placed by the row glyph's measured width, because a plain text takes one
colour.

A folder previews in the same scroller a file does, rather than in a second
`ListView` with its own delegate and its own way of being navigated. Its rows
are set the way the browser's own rows are — name at the left, size and date out
at the right edge — and filled down the pane and then across it: `dirRows` is how
many lines the pane is tall, `dirPaneChars` how many characters wide, so eight
files spread their facts across the full width and forty break into two columns.
A name too long for its column ends in `…`, cut short of an emoji rather than
through it.
A bare column of names left seven eighths of a pane as wide as a file of code
empty, and the answer was not a narrower pane.

Both panes start at the same height. A line of text sits at the top of its line
box while a list row sits in the middle of a taller one, so without `dirTopPad`
the first file in the preview floats above the first file in the list.

**A folder is read again in bursts, not once a file.** Entering one lists it at once.
After that, each change to the folder's count would snapshot and sort it whole, so
changes are read at most every 150 ms, and not at all while the panel is hidden: it
reads the folder once when it shows (`relistDue`).

Only what is near the view is **laid out**. A selection lays out two screens of
lines; scrolling within a screen of their end doubles that, and `End` lays out
the rest first, so the whole file is there to scroll through. The file is still
read whole: reading costs well under a millisecond, and editing needs it.
Laying out is the cost, and one Text lays out its lines in time growing with their
square, so code is laid out in pieces of 250 lines (`pieces()`). The pieces stay
from one change to the next, so one whose markup is unchanged keeps its layout and a
longer preview lays out only what it adds. Pygments closes its tags at every
newline, so each piece draws on its own; a line separator (U+2028) inside a
coloured token is the exception, and past a piece's edge the rest of that token is
plain. Each piece measures its own lines for `onLineLaidOut` and is as tall as its
lines, since StyledText drops a blank last one. `tests/files-preview.py` lays its
cases out in pieces of three, so every one crosses an edge.

Marks are read whenever the folder's rows load — which a save also triggers —
and whenever the browser opens; a short debounce combines duplicate requests,
and one status covers the folder previews too. `git-preview.py` sorts it into
a part per folder, and the browser reads only the listed folder's part and the
selected folder's, so moving between folders asks git nothing, and no folder
costs more than its own entries however many changes lie deeper. git reports
an untracked folder as one entry instead of walking it, so an unignored
`node_modules` costs one line rather than one per file; the status also names a path inside the listed
folder, which makes git open that folder even when it is untracked. A changed
file's diff is read when the selection settles, shown or not, so the heading
can count it. `git-preview.py` resolves missing directories through their
existing parent and chooses the comparison baseline. Each request owns its
process and collector; cancelled output cannot update a later selection, and
a stopped status read stops git too. Outside a repository the helper prints
nothing.
`node tests/files-index.js` and `node tests/files-git.js` exercise real Git
repositories; `python3 tests/runtime.py` also checks cancellation, deleted
directory navigation and backing out of it, large-file previews, and pairing
time in Quickshell.
`--no-optional-locks` keeps a status read off the index lock a commit may
want; `--literal-pathspecs` keeps `a*b` from diffing `axb` too.

**A folder's size is du's, for the settled folder only.** Sizing every listed folder
would walk whole trees for rows nobody looked at, and a reload around the same folder
does not start the walk over. `du -sbxD` is one process, so cancelling it on the next
selection stops the walk; a pipeline would orphan its children. `-x` keeps `/` from
walking `/proc` and mounts, `-D` measures a linked folder's target rather than the link,
and `-b` counts bytes as the file rows do. du exits non-zero when part of the tree is
unreadable but still prints a total, shown as `≥`. Sizes are kept by path for the session, so a
folder seen again shows its last size at once while du measures it anew.

**Properties** reuses that size and takes everything else from one `stat --printf` and
`file`. It stands in for the preview (`showsProps`) and goes when the settled path
changes, so the menu settles the row before opening it.

**A hovered name pops up whole** (`FilesTip.qml`, shared by the list and a folder's
preview). The list finds the row from the pointer's position on every move and scroll,
since a scroll moves rows under a still pointer without an enter or leave. Its
`HoverHandler` sits on the list's frame, since one inside a Flickable rides its content,
and the list sits above the preview so the name can run on over it. The preview uses the
entry its hover tint already finds and keeps the popup inside the pane.
`tests/files_info.py` checks the size, Properties and both popups in Quickshell.

## Writing

**One process, one contract.** Every write goes through the same `Process` and
the same exit codes: `0` done, `17` names taken with nothing pasted, `18` partial
paste with collisions, `19` partial paste with failures, anything else failed.
`op` carries what to say about each outcome, so move, copy, rename and delete
share one success path and one failure path rather than three of each.

**A long job says so, and can be stopped.** An `op` with `doing` is shown in the
header for as long as it runs, with its elapsed time; one with `reads` also gets a
percentage, how much of how much it has read, and a bar. That is a small `gauge` shell reading `/proc/<pid>/io`'s `rchar`
for the job's shell and its live children (`/proc/<pid>/task/<pid>/children`) once a
second, with builtins, so only its `sleep` forks. It counts against `du -scb` of the
inputs, its own process so it stops with the job rather than walking on, and whichever
of the two answers last shows the share. A shell takes in each child's count as it
reaps it, so a paste of many `cp`s counts every one exactly once, and the same number
works for `cp`, `mv`, `bsdtar` and `zip` with nothing to parse. bsdtar reads a zip's central directory first, so it runs a
little past the archive's size (68 MB over 9.8 GB with 397k entries); the bar clamps.

`Ctrl+K` sends `TERM` to the job's shell, then to its children. The shell must survive
that to clean up, so extract, compress and paste trap it (`STAY` sets `k`): the killed
`bsdtar` or `zip` fails into the cleanup it already had, and the paste loop stops
before the next item and removes the copy it was making. A move uses `mv` only within
one filesystem, where it is a rename. Across filesystems `mv` copies and deletes in one
process, and killed midway it leaves a partial target, which can't be told from a
complete one once a folder's source is half deleted. So the paste does `cp -a` and
removes the source only after the copy completes: a cancel during the copy removes the
copy, and one during the delete finds the copy complete. Killing only the shell would
orphan the child, which then runs on to the end with no one to clean up after it.

The pasted row arrives on its own: `FolderListModel` watches the directory, so
the paste only has to name what to land on — `pending`, the same mechanism the
wheel uses to hand a file over.

**Nothing is ever overwritten.** The destination is tested before the command runs:

    sh -c 'if [ -e "$2" ] || [ -L "$2" ]; then exit 17; fi; exec mv -- "$1" "$2"' files <src> <dst>

Paths go as arguments, never spliced into the script, so a space, a dash or a `$` is
just part of a name. `17` is nothing `mv` or `cp` return on their own; it comes back as
`a wheel.md is already here` rather than an invented `(copy)` name, since a file
manager that renames your file for you cannot be predicted. Directories go with
`cp -r`. `mkdir` and `touch` go through the same script with the verb as an argument,
and `Ctrl+Y` hands paths to `wl-copy` as arguments too.

**Delete trashes, and asks twice.** `gio trash` records the original path, so the entry
can be got back. The question is asked where you are looking: the row fills red and the
foot reads `del  again to trash <name>`. Any other key, a selection move, or three
seconds cancels it, so a second `Del` never lands on a row you did not aim at.

**Rename types into the filter chip**, already a text box sitting where the name
reads, with a different fill so it cannot pass for a filter. It is a real field
(caret keys, `Ctrl+U`/`Ctrl+K`, paste with separators stripped), opening with the caret
before the extension; the chip draws the name in two halves around the caret. A `/`
is refused: that is a move asked for in the wrong field.

**New file or folder: the name says which.** A dot makes a file, a trailing `/` a
folder and a trailing `.` a file, so `archive` and `v1.2/` are folders while
`notes.md`, `.gitignore` and `Makefile.` are files. A second binding would have been a
second thing to learn for a difference the name already spells out.

**The editor is modal**, because the keyboard is a filter: every printable key
otherwise lands in the search field. It edits plain source, not the rendering, since
saving a rendering would save pygments markup into the file; colour drops away while
editing. It edits only what it can write back whole: `fullText`, never the preview's
lines, and not a file over 256 KiB, binary, invalid UTF-8 (the bytes are checked, so a
real U+FFFD still edits), or one holding CR line endings, no-break spaces or a BOM,
which Qt's editor or `FileView` would change. Writes go out `atomicWrites`, are
confirmed by reading the file back (see Traps), and `endLine()` adds the trailing
newline vim would. A save rereads the file first: if it changed since the edit began,
the preview shows the new version, the draft stays, and saving again overwrites; a
file gone, unreadable or grown past 256 KiB is not saved over. `close()` routes to
`leaveEdit()` while there are unsaved changes, so a click outside arms the discard
rather than throwing the edit away.

**Your place is kept, as a fraction.** The editor sets its lines at the font's
own leading and the rendered preview does not, so a Markdown file is a wholly
different height in the two modes and the offset cannot be carried across —
`contentY` alone lands you somewhere unrelated in the document, which is what
made an edit at the foot of a file come back to the middle of it. `keepPlace()`
stores the fraction of the way down, `takePlace()` applies it when the scroller
re-measures (at the moment the mode flips, `contentHeight` is still the other
mode's), and the caret lands on the line you were reading.

## The menu

**It is drawn in the panel, not as a popup window.** An xdg-popup under a layer
surface that holds the keyboard exclusively would need keyboard routing of its own,
and a case each for the overlay, the window and the pinned search. In a window or
the pinned search it is the last child of `keys`, reparented with everything else;
over the overlay it covers the whole surface instead, so a submenu has the screen
beside the card rather than only the card. `FilesKeys` hands it keys the way it
hands them to naming or editing: it takes its own, and any other closes it and
falls through to the list's map.

**The rows are data.** `FilesActions.tree()` takes a context — the entry or the
marks, what the preview knows of the entry, what the probe found — and returns
rows with their `run`; `FilesMenu` only draws them. One table serves an entry and
the marks, which get the rows that take a list. It resolves the open submenu by
id so the probe can update its rows in place. The node tests read the same table
the menu draws.

**There is one submenu level.** `FilesMenuCard` is instantiated twice: the main
menu and its submenu stay mounted. `submenu` holds the open row's id, and `subAt`
holds the position beside that row. The submenu flips left when needed and resets
its scroll position when opened or switched. Switching submenus leaves the main
menu's rows intact.

A card uses a `Column` so its full height is known without waiting for a
`ListView` to create offscreen rows. `forceLayout()` places rows before keyboard
navigation measures them. Its row `Repeater` uses a count so a probe update can
replace row data without recreating every delegate.

Hover opens or switches submenus after 150 ms, measured from reaching the row.
Entering the submenu cancels a pending switch; clicking its parent row again
closes it until the pointer leaves that row.

**The menu holds its row.** Its rows act on the entry it opened on, which
`beginRename()` and `beginCopyName()` take as `named`, and what they make goes
beside that entry. `onRowsChanged` keeps the selection on the entry while the menu
is open, as it does for an edit, and closes the menu when the row is gone. An
entry of a folder's preview is no row (`aside`): the selection stays on that
folder, and Edit, which edits the preview, is not offered. Show changes on a
deleted child enters its containing folder and selects it before showing the diff.
Compress and Extract request landing only when their output is in the listed
folder, so a preview's output cannot select an unrelated same-named entry.

**Probe only what the menu uses.** `probeCommand()` queries executability and
MIME applications for a single existing entry. It asks for Taildrop targets only
when all targets are files; a marks menu containing folders needs no probe.
gio runs under `LC_ALL=C` because its headings are translated. A Taildrop target's
line carries a third field only when the device is offline.

**Open with launches as Omarchy's own launcher does** (`AppLibrary.launch`): a
terminal app through `omarchy-launch-tui`, with its command less the field codes,
and anything else through `uwsm-app -- gtk-launch`, which resolves ids uwsm rejects.

**`Del` in the menu is its Trash**, armed or not, so a menu on one entry never
arms another: the selection, or the marks. A menu without Trash consumes `Del`
without acting.

**Extract makes its scratch folder with `mkdir`, not `mktemp -d`,** whose 0700
would stay with the folder when it is renamed into place. **Convert checks its
name first** because `omarchy-transcode` would overwrite with `magick`: the check
is the process `FilesOps` runs, and its `then` starts the transcoder detached only
once the check has passed.

## Marks

**Marks are paths, and `marks` is read off the listing.** `marked` maps a path to
`true`; `marks` filters live `listedEntries` by it, excluding Git-deleted rows. So a filter hides marks without
dropping them, a file moved or trashed drops out of `marks` on its own, and only
leaving the folder clears the map. `targets` — the marks, or else the selection —
is what `Ctrl+X`/`C`/`Y` and `Del` hand to `FilesOps`, whose verbs take a list.
`hiddenMarks` counts targets absent from `rows`; the header, menu and trash
confirmation show that count. A marks menu closes when its target paths change.

**What Trash arms is the list's paths, joined by newlines.** The second press
trashes only when it names the same list, the rows red are the rows in that
string, and any change to the marks disarms it (`onMarkedChanged`) — a `Ctrl`+click
on the row already selected changes the marks without moving the selection, which
would otherwise leave a Trash armed for a different list.

**A paste is one process**, `pasteCommand()`, for one entry or many, which asks the
destination's filesystem once rather than once an item. It goes on past
a name already taken — its own, when pasted where it already is. `17` means every
name was, so nothing went and the hold stays. `18` means some names collided;
`19` means some entries succeeded and others failed. Both clear a move hold,
since it contains paths already moved. Total failure preserves the hold for retry.

`node tests/files-menu.js` holds each kind of entry to its rows, the marks to theirs,
drives the menu's and the marks' keys, and runs compress, extract, convert, duplicate,
link, paste-into and a paste of many against disposable files; `menu-pointer` in
`python3 tests/runtime.py` right-clicks and `Ctrl`+clicks the real list and opens its
submenus, with gio and tailscale stood in for. `tests/files-failures.js` covers
partial operations, extraction cleanup after failed renames, hidden target counts
and which commands each probe invokes. `tests/files-cancel.js` cancels a stubbed
extract, compress, copy and cross-filesystem move midway with the real cancel and checks nothing is left,
and reads a running job's gauge.

## Highlighting and Markdown

Colour comes from pygments, one process per settled selection, and a second for the
rest of a long file:

    python3 highlight.py <path> <lines>     one interpreter, style=one-dark

One interpreter does the lexer lookup and the formatting together; naming the
lexer with `pygmentize -N` would cost a second Python start and a shell to pipe
them. The selection's own 60 ms settle means arrowing through a directory does not
spawn a process per row. pygments' `get_lexer_for_filename` looks for plugin lexers
and compiles its ~900 name patterns on every start; `lexer_for()` makes the same
choice from the built-in table, a plain `*.ext` as a suffix test, and falls back to
pygments if that table changes shape. Colour is a
nicety: without `python3` or pygments the escaped plain text stays. It lands a beat
after the text (interpreter start); one long-lived process would be the next step. An image's pixel size
comes from ImageMagick's `identify`, also optional.

**The uncoloured file travels through the same markup the coloured one does.**
Swapping a plain-text item for a marked-up one steps the whole file down the
page the instant the highlighter answers; rendering both states through one
path makes the arrival of colour nothing but a change of colour.

**That markup is StyledText, drawn exactly as a rich-text `<pre>` drew it.**
StyledText lays out far faster than the `<pre>` it replaced. `styledCode()` and `highlight.py` keep the
`<pre>` rules: no newline straight after the opening tag or before the closing
one, no `\r`, every other whitespace character kept, as entities StyledText
cannot collapse. Rich text put each baseline 4/5 down its fixed-height line
whatever the fonts; StyledText puts it at the line's ascent, so `onLineLaidOut`
moves every line back, measuring with a hidden probe any line that leaves
printable ASCII. NEL goes in as U+0080, another glyphless control, because Qt
reads `&#133;` as an ellipsis. `tests/files-preview.py` holds all of it to the
old rendering pixel for pixel.

`highlight.py` colours the file's first lines, split at `\n` alone as Qt splits
them: first `2 × shownLines + 2`, so a preview doubled before the rest lands stays
coloured and still ends in `head()`'s `…` (a blank last line would read as the end),
then the whole file, so scrolling on and `End` find it coloured. The lexer sees the
whole source, including closing delimiters past the cut; token consumption and
formatting stop at the line break that ends it, so those lines colour as they would
in the whole file, a blank last one included. The preview shows its first
`shownLines`: the gutter numbers `head()` of the text, and the markup is cut by the
same `head()` at its `<br>`s, appending the same `…` line, for the same reason: if
the two disagree the numbers stop naming the lines beside them.

Markdown is rendered by Qt; two things have to be done to the source first.

**Links are flattened to their words.** Qt paints Markdown links in a blue of
its own that belongs to no theme on this card and is barely legible on a dark
ground, and `linkColor` does not override what the Markdown importer stamps on
them. A preview pane cannot follow a link anyway.

**Blank lines are given a paragraph to occupy.** Qt's Markdown importer gives a
paragraph *no margins*, so a rendered document arrives as one unbroken slab
whatever line height it is set at — headings included. `airOut()` replaces each
blank line with a paragraph holding a single non-breaking space, which
CommonMark counts as content rather than as more blank. Fenced blocks are left
exactly as written.

**Markdown has a `Text` of its own.** When one `Text` served both, its line
height switched with the format and it carried the code's per-line handler, and
Qt then laid out Markdown tables many times slower. Do not fold the two back
together.

## Traps

**`FolderListModel` is snapshotted, not bound.** Qt's model does not apply
`nameFilters` to directories, so a filter typed into it narrows the files and
leaves every folder standing; and it sorts on one field, where a browser wants
folders first *and* the filter's best match first *and* then alphabetical.
`FilesIndex.snapshot()` costs one pass per directory entered and buys both.

**`FolderListModel` can list the wrong folder.** It turns its URL into a path
and parses that as a URL again, so a `#`, `?` or `%XX` in a folder name cuts
the path short, encoded or not (raw, encoded and double-encoded URLs were all
tried on Qt 6.12): `#archive` lists its parent. A fresh model given
a folder that is not there lists the working directory. `snapshot()` drops
every row not inside the folder asked for, so `Delete` or `F2` can never reach
another folder's files; such a folder shows "Can't list this folder" or
"Empty". Images and videos take `fileUrl()`, which carries `#` and `?` through.

**An unreadable folder lists as empty.** `FolderListModel` has no permission
roles, and a folder you may not read, or one that is gone, gives the same
Ready and no rows as an empty one. So each folder entered, and a previewed one
that lists empty, is asked with `test -r -x`; one that fails shows "Can't list
this folder".

**A folder still listing holds the last one's rows.** Moved to another folder,
`FolderListModel` keeps the previous rows until the new listing arrives, and
`snapshot()` drops them as another folder's. A slow listing, such as a network
share mounting after its idle timeout, would read as "Can't list this folder",
so neither pane says anything while its model is `Loading`.

**Hover never claims the selection.** The selection is what `Return`, `F2` and
`Delete` act on, so only a click moves it. When hover claimed it, a pointer
drifting over the list moved the selection while you typed a rename, and `Return`
renamed whichever file it had drifted to.

**The selection is a row number, so an edit or rename holds its file.** A save
re-sorts the folder by date or size, and a download lands above you in any order;
the same index then names another file. While editing or renaming,
`onRowsChanged` moves the index back onto the file, and `save()` writes only to
the path `edit()` began on, refusing if the preview has moved anyway.

**A landing scrolls the list only once the list holds the new rows.**
`onRowsChanged` can run before the `ListView` takes the new model, and scrolling
then moves the old rows: the selection landed far down a folder while the list
stayed at the top. `claimPending()` asks for the scroll with `Qt.callLater`.

**A change handler can see a stale binding.** `showsCode` is a binding on
`previewText`, and `onFullTextChanged` can run *before* that binding
re-evaluates — so asking it there reads the value from before the file loaded,
and the highlighter never starts. Imperative code asks the two conditions
directly; only the declarative bindings use `showsCode`. The guard is deliberate; do not "simplify" it back.

**The monitor is resolved once, when the panel opens.** Hyprland moves focus
with the pointer, so a live binding would walk the surface onto another monitor
while you are reading it. Matched by name, because this Quickshell's
`HyprlandMonitor` carries no `screen`.

**Opening a file closes the panel only if something is opening.** Whatever
opens wants the keyboard, and the layer surface holds it exclusively until it
unmaps — but a file the desktop has no viewer for opens nothing, and closing the
browser for it would look like the panel had crashed. `omarchy-open-path` is run
as a `Process` and the exit code decides: `0` closes, `3` and `4` stay.

Of the two declines, only `4` says anything. `3` is a terminal handler for a
file that is not text, and on Omarchy the terminal handler is usually nvim, so it hardly
happens. `4` is nothing owning it at all, and there the panel says `nothing
here opens <name>`: with no pane covering for it, silence reads as a key that
did nothing.

**`FileView` does not tell you whether a write worked.** Neither `saved` nor
`saveFailed` fires for `setText`; a permission failure only prints a warning.
A `reload()` in the same tick as the write is also swallowed, which is what the
150 ms is for. The other way round, a write started inside `onLoaded` drops the
read that is finishing, so the save's pre-write check (`checking` against
`editBase`, refusing undecoded a file grown past `previewLimit`) defers its
write with `Qt.callLater`. A failed read-back ends the save as failed
(`onLoadFailed`), or every later save would wait on it.

**`TextEdit` has no `lineHeight`.** It is a `Text` property, not a
`QQuickTextEdit` one, so an edited file is set at the font's own leading rather
than the preview's 1.75 rhythm, and edit mode is unavoidably denser. The gutter
has to follow it twice over: `ProportionalHeight` *and* the body's font size,
because a font's leading follows its size — under the fixed rhythm the numbers
can be smaller, since there the rhythm is what aligns them, but at natural
leading a smaller gutter drifts off its own lines down the page.

**Reopening where you already are announces nothing.** `enter()` sets the same
`dir`, `FolderListModel` reloads nothing, `rows` is the same array — so
`onRowsChanged` never fires and `claimPending()` is never reached, leaving the
selection on row 0 instead of on the file the wheel named. `sel` has not changed
either, so `settle` never restarts and `settledSel` — dropped on close — stays
null, which the preview renders as `Empty` over a file sitting right there. So
`open()` calls `claimPending()` directly and restarts the settle. The name is
cleared only once found, or by `enter()` — walking somewhere yourself abandons
it — so the direct call cannot discard it a frame before its rows arrive.

**The scroller's content height is not the content's height.** Both panes sit
`dirTopPad` down the Flickable so the first line aligns with the first list row.
Counting only `content.height` leaves that offset unreachable, so the last line
of a file is clipped by the bottom edge — on the file you scrolled to the bottom
to read. It is counted twice, which also gives the closing line the air the
opening one stands in.

**Raw HTML in a Markdown file eats the rest of the document.** Qt's importer
hands anything tag-shaped to a sub-parser, and an unclosed tag swallows every
block after it — only code spans come through, because those arrive as their own
typed spans rather than as text. One `<dir>` written inside a sentence in
`docs/wheel.md` cut the preview from 17907 rendered characters to 7477, and the
tail of the file read as a column of empty bullets. `escapeTags()` escapes every
angle bracket outside code, so a tag is shown as it was written; code spans and
fenced and indented blocks are left alone, where `&lt;` would be four literal
characters rather than one.

**Both `FolderListModel` handlers are gated on `Ready`.** A load raises `count`
on its way to `Ready`, so ungated the model was snapshotted twice per directory
and flashed empty in between. `onCountChanged` is still needed for a file
appearing under an open panel, which raises `count` with the model already
`Ready`.

**A change handler sees the bindings on its property still on the last value.**
QML calls a property's handlers before the bindings that read it, which connect
later, so `onSettledSelChanged` reading `showsImage` got the previous entry's
answer: an image after a text file was never measured, and an image giving way to
nothing read the path of `null`. The handler and `readDiff()` ask `media()` of the
entry itself, and the bindings ask the same function, so the two cannot disagree.

## Wiring

**Popping out.** `Ctrl+T` sets `windowed` before clearing `opened`, so the panel stays
shown and the folder, selection and preview carry into a plain `FloatingWindow` that
Hyprland tiles like any other. To the shell the browser is then closed: opening the
wheel or a panel leaves the window alone, `SUPER+W` closes it, and `Esc` only clears the
field. A file picked in the wheel sends the window there; a summon without a path only
focuses it. A file picked in the pinned search opens the browser inside that search's
window as its `guest` instead. A window close cannot ask twice, so an unsaved edit
brings the overlay back holding the edit.

`bin/omarchy-open-path` is on `PATH` because a plugin directory is private to
its owner. It routes by handler rather than calling `xdg-open` blindly:
on a typical Omarchy install `text/plain` resolves to `nvim.desktop`, and `xdg-open` launches that with
no terminal attached, so nvim hangs invisibly and `Enter` looks like it did
nothing.

So text that no graphical app owns — a terminal handler like that one, or no
handler at all, as `.js`, `.sh` and `.json` often have none — goes to
`omarchy-launch-editor`, which opens Omarchy's default editor and gives a
terminal editor its terminal. An empty file counts as text: a new file is
written there too. Anything else with a terminal handler is a
decline: the script exits `3`, and the browser keeps its place. An image, a PDF,
a video goes to `xdg-open`, and a zero exit is what tells the browser to step
aside for it. `python3 tests/open-path.py` runs each route with the handlers and
launchers stubbed.

The wheel registers it in `MenuIndex.js` as an `EXTRAS` entry — searchable
without consuming a ring slice, so the default ring keeps the even count that
fills 3 and 9 o'clock. It is ranked with the panels rather than the apps, which is what puts it above
GNOME Files, whose entry is also called "Files".

The backdrop is not this surface's. The wash and the blur behind the card
belong to one scrim owned by the bar, which the panels, the wheel and the
clipboard hold a count on too — so opening the browser from the wheel changes
what stands on the backdrop without the backdrop itself going anywhere. This
surface only asks for that count when it opens (`Files.qml` `onOpenedChanged`)
and lets it go when it closes; the bar holds the scrim 150 ms past the last
release, which covers the ~55 ms a replacement surface takes to map.
