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
    filer.command = command
    filer.running = true
  }

  // Pass paths as arguments to preserve shell metacharacters.
  function guarded(verb, src, dst) {
    return ["sh", "-c", 'if [ -e "$2" ] || [ -L "$2" ]; then exit 17; fi; exec ' + verb + ' -- "$1" "$2"',
            "files", src, dst]
  }

  function inHere(name) { return root.panel.listedDir.replace(/\/+$/, "") + "/" + name }

  // Each into the folder in turn, past a name already taken, its own name included: 17 when every
  // name was taken, 18 when only some were, 1 when any failed.
  function pasteCommand(move, dir, paths) {
    return ["sh", "-c", 'v=$1 d=$2; shift 2; s=0 p=0; for f do t="$d/${f##*/}"; '
      + 'if [ -e "$t" ] || [ -L "$t" ]; then [ "$s" = 1 ] || s=17; elif $v -- "$f" "$t"; then p=1; else s=1; fi; done; '
      + '[ "$s" = 17 ] && [ "$p" = 1 ] && s=18; exit $s',
      "files", move ? "mv" : "cp -r", dir].concat(paths)
  }

  // Into the folder being listed, or into the folder given; only the first lands in view.
  function paste(into) {
    var h = root.held
    if (!h) return
    root.run(root.pasteCommand(h.move, into || root.panel.listedDir.replace(/\/+$/, ""), h.items.map(i => i.path)),
             { name: h.items[0].name, land: !into, spend: h.move,
               taken: "some names were already here; the rest " + (h.move ? "moved" : "copied"),
               done: (h.move ? "moved " : "copied ") + h.name + (into ? " into " + into.slice(into.lastIndexOf("/") + 1) : ""),
               fail: (h.move ? "move" : "copy") + " failed" })
  }

  Process {
    id: filer
    onExited: function (exitCode) {
      var o = root.op
      root.op = null
      if (!o) return
      if (exitCode !== 0) {
        root.note(exitCode === 17 ? "a " + o.name + " is already here" : exitCode === 18 && o.taken ? o.taken : o.fail)
        // Some of many went, so the hold no longer names what is there to move.
        if (exitCode === 18 && o.spend) root.held = null
        return
      }
      if (o.land) root.panel.pending = o.name
      root.note(o.done)
      if (o.spend) root.held = null
      // A check that passed hands over to the job it checked for, which reports on its own.
      if (o.then) Quickshell.execDetached(o.then)
    }
  }
  // Many paths go one to a line.
  function copyPath(entries) {
    if (!entries.length || root.panel.editing) return
    root.run(["sh", "-c", 'printf %s "$1" | wl-copy', "files", entries.map(e => e.path).join("\n")],
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
  readonly property string doomedName: !root.doomed ? ""
    : root.doomed.indexOf("\n") >= 0 ? root.doomed.split("\n").length + " items"
    : root.doomed.slice(root.doomed.lastIndexOf("/") + 1)
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
             { name: entries[0].name, done: "trashed " + root.label(entries), fail: "delete failed" })
  }
  // Keep the panel open unless another application accepts the file.
  property var opening: null
  function activate(e) {
    if (!e || root.panel.editing) return
    if (e.isDir) { root.panel.enter(e.path); return }
    if (e.missing) { root.panel.diffMode = true; return }
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
