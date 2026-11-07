import QtQuick
import Quickshell
import Quickshell.Io
import "FilesIndex.js" as FilesIndex

// File mutations are serialized here and never overwrite existing paths.
Item {
  id: root

  property var panel: null

  // Held copy/move state survives directory navigation.
  property var held: null
  property string fileNote: ""
  Timer { id: noteFade; interval: 4000; onTriggered: root.fileNote = "" }
  function note(text) { root.fileNote = text; noteFade.restart() }

  // The verbs take a list of entries. What a list is called: its one entry, or how many.
  function label(entries) { return entries.length > 1 ? entries.length + " items" : entries[0].name }

  // A deleted row or a root's cannot be held.
  function hold(entries, move) {
    entries = entries.filter(e => !e.missing && !e.shortcut)
    if (!entries.length) return
    root.held = { items: entries.map(e => ({ path: e.path, name: e.name })), move: !!move, name: root.label(entries) }
    root.note((move ? "moving " : "copying ") + root.held.name)
  }

  // Exit 17 is reserved for destination collisions.
  property var op: null
  function run(command, about) {
    if (filer.running) { root.note("a file operation is still running"); return }
    root.op = about
    root.cancelling = false
    root.progress = -1
    root.elapsed = 0
    if (about.doing) root.fileNote = ""
    filer.command = command
    filer.running = true
  }

  // A job that says what it is doing shows it for as long as it runs, how far it has read of what it
  // reads, and stops on Ctrl+K.
  property bool cancelling: false
  property real progress: -1
  property int elapsed: 0
  readonly property bool busy: !!root.op && !!root.op.doing
  // The header sets the percentage between the two, in a colour of its own.
  readonly property string statusHead: root.busy ? root.op.doing : ""
  readonly property string statusTail: !root.busy ? "" : root.cancelling ? " · cancelling"
    : " · " + Math.floor(root.elapsed / 60) + ":" + String(root.elapsed % 60).padStart(2, "0") + " · ctrl+k cancels"
  readonly property string percent: root.busy && !root.cancelling && root.progress >= 0 ? Math.round(root.progress * 100) + "%" : ""
  Timer { running: root.busy; interval: 1000; repeat: true; onTriggered: root.elapsed++ }

  // The shell first, which a job that cleans up traps rather than dies of, then what it is running.
  function cancel() {
    if (!root.busy) return
    root.cancelling = true
    Quickshell.execDetached(["sh", "-c", 'kill -TERM "$1"; pkill -TERM -P "$1"', "cancel", String(filer.processId)])
  }

  // What the job has read: its own count and its running children's, since a shell takes in each
  // child's count as it reaps it. Once a second while it runs, read with builtins rather than a
  // process per child; only sleep forks.
  function gaugeCommand(pid) {
    return ["sh", "-c", 'p=$1; while kill -0 "$p" 2>/dev/null; do r=0 kids=; read -r kids 2>/dev/null < "/proc/$p/task/$p/children"; '
      + 'for c in "$p" $kids; do while read -r k v; do [ "$k" = rchar: ] && { r=$((r + v)); break; }; done 2>/dev/null < "/proc/$c/io"; done; '
      + 'echo "$r"; sleep 1; done', "gauge", String(pid)]
  }
  Process {
    id: gauge
    property real done: 0
    stdout: SplitParser { onRead: line => { gauge.done = +line; root.showProgress() } }
  }
  // Against the size of its inputs: one du, so it stops with the job rather than walking on.
  // Whichever of the two answers last shows the share.
  property real total: 0
  FilesProcess {
    id: totaller
    onFinished: output => { root.total = parseInt(output.trim().split("\n").pop(), 10) || 0; root.showProgress() }
  }
  function showProgress() { if (root.total > 0) root.progress = Math.min(1, gauge.done / root.total) }

  // Pass paths as arguments to preserve shell metacharacters.
  function guarded(verb, src, dst) {
    return ["sh", "-c", 'if [ -e "$2" ] || [ -L "$2" ]; then exit 17; fi; exec ' + verb + ' -- "$1" "$2"',
            "files", src, dst]
  }

  function inHere(name) { return root.panel.listedDir.replace(/\/+$/, "") + "/" + name }

  // Each into the folder in turn, past a name already taken, its own name included: 17 when every
  // name was taken, 18 when some were, 19 on partial failure, 1 on total failure. A move to another
  // filesystem is a whole copy before the source goes, so a cancel removes only an unfinished copy
  // and stops before the next.
  function pasteCommand(move, dir, paths) {
    return ["sh", "-c", 'v=$1 d=$2; shift 2; s=0 p=0; trap "k=1" TERM; [ "$v" = mv ] && e=$(stat -c %d -- "$d"); put() { '
      + 'if [ "$v" = mv ] && [ "$(stat -c %d -- "$1")" = "$e" ]; then mv -- "$1" "$2"; return; fi; '
      + 'if [ "$v" = mv ]; then o=-a; else o=-r; fi; '
      + 'if ! cp $o -- "$1" "$2"; then [ -z "$k" ] || rm -rf -- "$2"; return 1; fi; [ "$v" = cp ] || rm -rf -- "$1"; }; '
      + 'for f do [ -z "$k" ] || break; t="$d/${f##*/}"; '
      + 'if [ -e "$t" ] || [ -L "$t" ]; then [ "$s" = 1 ] || s=17; elif put "$f" "$t"; then p=1; else s=1; fi; done; '
      + '[ -z "$k" ] || exit 130; if [ "$p" = 1 ]; then [ "$s" = 17 ] && s=18; [ "$s" = 1 ] && s=19; fi; exit $s',
      "files", move ? "mv" : "cp", dir].concat(paths)
  }

  // Into the folder being listed, or into the folder given; only the first lands in view.
  function paste(into) {
    var h = root.held
    if (!h) return
    root.run(root.pasteCommand(h.move, into || root.panel.listedDir.replace(/\/+$/, ""), h.items.map(i => i.path)),
             { name: h.items[0].name, land: !into, spend: h.move, reads: h.items.map(i => i.path),
               doing: (h.move ? "moving " : "copying ") + h.name,
               occupied: h.items.length > 1 ? "all " + h.items.length + " names are already here" : "a " + h.name + " is already here",
               taken: "some names were already here; the rest " + (h.move ? "moved" : "copied"),
               partial: "some items " + (h.move ? "moved" : "copied") + "; others could not be " + (h.move ? "moved" : "copied"),
               done: (h.move ? "moved " : "copied ") + h.name + (into ? " into " + into.slice(into.lastIndexOf("/") + 1) : ""),
               fail: (h.move ? "move" : "copy") + " failed" })
  }

  Process {
    id: filer
    onStarted: {
      if (!root.op || !root.op.reads) return
      root.total = gauge.done = 0
      totaller.start(["du", "-scb", "--"].concat(root.op.reads))
      gauge.command = root.gaugeCommand(filer.processId)
      gauge.running = true
    }
    onExited: function (exitCode) {
      var o = root.op
      root.op = null
      gauge.running = false
      totaller.cancel()
      if (!o) return
      if (root.cancelling && exitCode !== 0) {
        root.note(o.doing.replace(/^\S+ /, "") + " cancelled")
        return
      }
      if (exitCode !== 0) {
        root.note(exitCode === 17 ? o.occupied || "a " + o.name + " is already here"
                  : exitCode === 18 && o.taken ? o.taken : exitCode === 19 && o.partial ? o.partial : o.fail)
        // Some of many went, so the hold no longer names what is there to move.
        if ((exitCode === 18 || exitCode === 19) && o.spend) root.held = null
        return
      }
      if (o.land) root.panel.pending = o.name
      root.note(o.done)
      if (o.spend) root.held = null
      // A check that passed hands over to the job it checked for, which reports on its own.
      if (o.then) Quickshell.execDetached(o.then)
    }
  }
  // Many paths go one to a line, each its own argument: Linux caps any one at 128 KiB.
  function copyPath(entries) {
    if (!entries.length || root.panel.editing) return
    root.run(["sh", "-c", '{ printf %s "$1"; shift; [ $# = 0 ] || printf "\\n%s" "$@"; } | wl-copy', "files"].concat(entries.map(e => e.path)),
             { done: "copied " + (entries.length > 1 ? entries.length + " paths" : FilesIndex.display(entries[0].path, root.panel.home)),
               fail: "copy path failed" })
  }
  // A terminal in the folder being browsed, or in the folder given.
  function terminal(dir) {
    root.launch(["uwsm-app", "--", "xdg-terminal-exec", "--dir=" + (dir || root.panel.dir)])
  }
  // Another app takes over: the panel unmaps first, since it holds the keyboard the app will ask for.
  function launch(argv) {
    root.panel.close()
    Quickshell.execDetached(argv)
  }
  // A job that reports on its own, as a transfer does: started, and left to it.
  function detach(argv, text) {
    Quickshell.execDetached(argv)
    root.note(text)
  }
  // Deletion uses trash, requires two presses, and stays visibly red across themes. What is armed is
  // the list's paths, joined, so the second press trashes exactly what the first showed.
  readonly property color danger: "#ff2222"
  property string doomed: ""
  readonly property string doomedName: {
    if (!root.doomed) return ""
    var paths = root.doomed.split("\n")
    var name = paths.length > 1 ? paths.length + " items" : root.doomed.slice(root.doomed.lastIndexOf("/") + 1)
    var hidden = root.doomed === root.panel.marks.map(e => e.path).join("\n") ? root.panel.hiddenMarks : 0
    return name + (hidden ? " (" + hidden + " hidden)" : "")
  }
  Timer { id: doomArmed; interval: 3000; onTriggered: root.doomed = "" }
  function remove(entries) {
    if (!entries.length || entries.some(e => e.missing || e.shortcut) || root.panel.editing) return
    var paths = entries.map(e => e.path)
    if (root.doomed !== paths.join("\n")) {
      root.doomed = paths.join("\n")
      doomArmed.restart()
      return
    }
    root.doomed = ""
    root.run(["gio", "trash", "--"].concat(paths),
             { name: entries[0].name, doing: "trashing " + root.label(entries),
               done: "trashed " + root.label(entries), fail: "delete failed" })
  }
  // Keep the panel open unless another application accepts the file.
  property var opening: null
  function activate(e) {
    if (!e || root.panel.editing) return
    if (e.isDir) { root.panel.enter(e.path); return }
    if (e.missing) {
      // A preview's deleted child needs its own selection for the diff reader.
      if (!root.panel.sel || root.panel.sel.path !== e.path) {
        root.panel.enter(e.path.slice(0, e.path.lastIndexOf("/")) || "/")
        root.panel.pending = e.name
        root.panel.claimPending()
      }
      root.panel.diffMode = true
      return
    }
    root.opening = e
    opener.command = ["omarchy-open-path", e.path]
    opener.running = true
  }

  Process {
    id: opener
    onExited: function (exitCode) {
      if (exitCode === 0) { root.panel.close(); return }
      // Exit 3 is a quiet decline; exit 4 means no application claimed the file.
      if (exitCode !== 4) return
      root.note("nothing here opens " + root.opening.name)
    }
  }
}
