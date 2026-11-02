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

`FilesIndex.within()` is applied on every path change — arrow navigation, `←`,
`Backspace`, and typed paths alike — after `cleanPath()` has collapsed `.` and `..`
segments, so a typed `..` cannot step over the jail; a symlink inside home that
points outside is not resolved, and is followed.

`within()` tests `root + "/"` rather than a bare prefix, because `/home/alex2` starts
with `/home/alex` and is not inside it. `display()` tildes only home
itself or a path under `home + "/"` for the same reason.

## Layout, preview and git status

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

Only what is near the view is **laid out**. A selection lays out two screens of
lines; scrolling within a screen of their end doubles that, and `End` lays out
the rest first, so the whole file is there to scroll through. The file is still
read whole: reading costs well under a millisecond, and editing needs it.
Laying out is the cost.

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

## Writing

**One process, one contract.** Every write goes through the same `Process` and
the same exit codes: `0` done, `17` the name is taken, anything else failed.
`op` carries what to say about each outcome, so move, copy, rename and delete
share one success path and one failure path rather than three of each.

The pasted row arrives on its own: `FolderListModel` watches the directory, so
the paste only has to name what to land on — `pending`, the same mechanism the
wheel uses to hand a file over.

**Your place is kept, as a fraction.** The editor sets its lines at the font's
own leading and the rendered preview does not, so a Markdown file is a wholly
different height in the two modes and the offset cannot be carried across —
`contentY` alone lands you somewhere unrelated in the document, which is what
made an edit at the foot of a file come back to the middle of it. `keepPlace()`
stores the fraction of the way down, `takePlace()` applies it when the scroller
re-measures (at the moment the mode flips, `contentHeight` is still the other
mode's), and the caret lands on the line you were reading.

## Highlighting and Markdown

Colour comes from pygments, one process per settled selection:

    python3 highlight.py <path>             one interpreter, style=one-dark

One interpreter does the lexer lookup and the formatting together; naming the
lexer with `pygmentize -N` would cost a second Python start and a shell to pipe
them. A 60 ms debounce means arrowing through a directory does not spawn a
process per row.

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

`highlight.py` colours the whole file once. The preview shows its first
`shownLines`: the gutter numbers `head()` of the text, and the markup is cut by
the same `head()` at its `<br>`s, appending the same `…` line, for the same
reason: if the two disagree the numbers stop naming the lines beside them.

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
the path short, encoded or not: `#archive` lists its parent. A fresh model given
a folder that is not there lists the working directory. `snapshot()` drops
every row not inside the folder asked for, so `Delete` or `F2` can never reach
another folder's files; such a folder shows "Can't list this folder" or
"Empty". Images and videos take `fileUrl()`, which carries `#` and `?` through.

**An unreadable folder lists as empty.** `FolderListModel` has no permission
roles, and a folder you may not read, or one that is gone, gives the same
Ready and no rows as an empty one. So each folder entered, and a previewed one
that lists empty, is asked with `test -r -x`; one that fails shows "Can't list
this folder".

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
150 ms is for.

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

## Wiring

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
