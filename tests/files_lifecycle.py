"""Closed file panels must not restart previews when their directory changes, and popping out
into a window must keep the preview it had. Rows follow every change to the directory, query and order."""


def check(files, run, block, line):
    run("files-lifecycle", '''
  property bool opened: false
  property bool windowed: false
  property var shell: null
  property var sel: null
  property var settledSel: null
  property bool editing: false
  property bool dirty: false
  property bool discarding: false
  property string naming: ""
  property int stage: 0
  property var entries: []
  readonly property var listedEntries: entries
  property string query: ""
  property string order: "name"
  QtObject { id: ops; property string doomed: "" }
  function readChanges() {}
  QtObject { id: gitStatus; function cancel() {} }
  QtObject { id: statusSoon; function stop() {} }
  function check(ok, message) {
    if (!ok) { console.error("FAIL", message); Qt.exit(1) }
  }
''' + line(files, r"^  readonly property bool shown: .*") + line(files, r"^  readonly property var orderedEntries: .*")
        + line(files, r"^  readonly property var rows: .*") + line(files, r"^  onSelChanged: .*")
        + "\n".join(block(files, pattern) for pattern in [r"^  onShownChanged: \{", r"^  Timer \{\n    id: settle",
                                                          r"^  function popOut\(\) \{"]) + '''
  Component.onCompleted: {
    entries = [{ name: "zAlpha", size: 9, isDir: false },
               { name: "alpha", size: 2, isDir: false }]
    query = "alpha"
    check(rows[0].name === "alpha", "prefix ordering")
    order = "size"
    check(rows[0].name === "zAlpha", "order change did not rebuild sorting")
    entries = [{ name: "newAlpha", size: 3, isDir: false }]
    check(rows.length === 1 && rows[0].name === "newAlpha", "directory update left stale rows")
    query = "missing"
    check(rows.length === 0, "query change left stale rows")
    query = ""
    check(rows.length === 1, "clearing query lost full listing")
    sel = ({ path: "initial" })
  }
  Timer { interval: 120; running: true; repeat: true; onTriggered: {
    switch (root.stage++) {
    case 0:
      root.check(!root.settledSel, "initial closed selection started preview")
      root.opened = true; break
    case 1:
      root.check(root.settledSel === root.sel, "opening did not preview cached selection")
      root.sel = ({ path: "visible-change" }); break
    case 2:
      root.check(root.settledSel === root.sel, "visible selection did not settle")
      root.editing = root.dirty = root.discarding = true; root.naming = "rename"
      root.opened = false
      root.sel = ({ path: "hidden-change" }); break
    case 3:
      root.check(!root.settledSel, "hidden directory update restarted preview")
      root.check(!root.editing && !root.dirty && !root.discarding && !root.naming,
                 "close retained editing, dirty, discard or naming state")
      root.opened = true; break
    case 4:
      root.check(root.settledSel === root.sel, "reopen did not preview updated selection")
      root.sel = ({ path: "pending" }); root.opened = false; break
    case 5:
      root.check(!root.settledSel, "close did not cancel pending preview")
      root.opened = true; break
    case 6:
      root.editing = root.dirty = root.discarding = true; root.naming = "new"
      root.popOut()
      root.check(root.settledSel === root.sel, "popping out dropped the preview")
      root.check(root.editing && root.dirty && root.discarding && root.naming === "new",
                 "popping out discarded active editing state")
      root.sel = ({ path: "windowed-change" }); break
    case 7:
      root.check(root.settledSel === root.sel, "windowed selection did not settle")
      root.sel = ({ path: "closing" }); root.windowed = false; break
    case 8:
      root.check(!root.settledSel, "closing the window did not cancel pending preview")
      root.check(!root.editing && !root.dirty && !root.discarding && !root.naming,
                 "closing the window retained editing state")
      console.log("PASS"); Qt.quit()
    }
  } }
''')

    # A save that reorders the folder, or a file landing above, must not move an edit or rename.
    run("files-rows-hold-edit", '''
  property int index: 0
  property var settledSel: null
  property bool editing: false
  property string naming: ""
  property var entries: []
  readonly property var listedEntries: entries
  property string query: ""
  property string order: "date"
  function claimPending() {}
  function file(name, modified) { return { name: name, path: "/d/" + name, modified: modified, isDir: false } }
  function check(ok, message) {
    if (!ok) { console.error("FAIL", message); Qt.exit(1) }
  }
''' + line(files, r"^  readonly property var orderedEntries: .*") + line(files, r"^  readonly property var rows: .*")
        + line(files, r"^  readonly property var sel: .*\n.*") + block(files, r"^  onRowsChanged: \{") + '''
  Timer { interval: 50; running: true; onTriggered: {
    entries = [file("a", 2000), file("b", 1000)]
    index = 1; settledSel = sel; editing = true
    entries = [file("a", 2000), file("b", 3000)]
    check(sel.path === "/d/b", "a save that made the file newest moved the edit to another file")
    editing = false; naming = "rename"
    entries = [file("a", 2000), file("b", 3000), file("c", 4000)]
    check(sel.path === "/d/b", "a new file above moved the rename to another file")
    naming = ""
    entries = [file("a", 2000), file("b", 3000), file("c", 5000), file("d", 6000)]
    check(sel.path === "/d/c", "browsing rows no longer stay by position")
    console.log("PASS"); Qt.quit()
  } }
''')
