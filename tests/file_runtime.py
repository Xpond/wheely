"""Actual file editing, file-operation process completion, and clicks in a folder's preview."""
import json
import os
import re
from file_edits import check as check_file_edits


def check(files, ops, base, run, block):
    check_file_edits(files, base, run, block)

    # The real preview under real pointer events: the entry under the pointer is tinted, a click picks
    # its column and line, a double click opens the pick, a right-click opens its menu without picking
    # it, and the wheel still scrolls the preview.
    run("preview-pointer", '''
  property var entries: Array.from({ length: 200 }, (_, i) => ({ name: "e" + i, path: "/t/e" + i, isDir: false, size: 1, modified: null }))
  property var dirColumns: FilesIndex.columns(root.entries, 10, 120, 400, ({}))
  property var dirMarks: []
  property bool showsDir: true
  property int lineHeight: 20
  property int dirTopPad: 5
  property int gutterGap: 16
  property int shownLines: 10
  property bool dirty: false
  property bool editing: false
  property bool previewCut: false
  property bool showAll: false
  property bool showsCode: false
  property bool showsDiff: false
  property bool showsImage: false
  property bool showsVideo: false
  property bool showsMarkdown: false
  property string previewBody: ""
  property string previewNote: ""
  property string previewText: ""
  property string shownText: ""
  property var settledSel: null
  property color hoverFill: "gray"
  property var picks: []
  property var sel: ({ name: "the folder" })
  property string naming: ""
  property QtObject menu: QtObject { function openAt(item, x, y, entry) { root.picks.push("menu " + entry.name) } }
  function previewEntry(column, line) { return FilesIndex.columnEntry(root.entries, 10, 120, 400, column, line) }
  function pickPreview(column, line) { root.picks.push(column + ":" + line) }
  function openPicked() { root.picks.push("open") }
  Pointer { id: pointer }
  Window { width: 900; height: 400; visible: true; FilesPreview { id: preview; panel: root; anchors.fill: parent } }
  function find(test) { var out = [], walk = item => item.children.forEach(c => { if (test(c)) out.push(c); walk(c) }); walk(preview); return out }
  Timer { interval: 200; running: true; onTriggered: {
    var column = root.find(c => c.text === root.dirColumns[1])[0], p = column.mapToItem(preview, 10, 3 * 20 + 10)
    pointer.mouseMove(preview, p.x, p.y, -1, Qt.NoButton, Qt.NoModifier)
    var tint = root.find(c => c.line !== undefined && c.column !== undefined && c.visible)[0]
    if (!tint || tint.mapToItem(column, 0, 0).y !== 3 * 20) { console.error("FAIL hovering an entry did not tint its line"); Qt.exit(1); return }
    pointer.mouseClick(preview, p.x, p.y, Qt.LeftButton, Qt.NoModifier, -1)
    pointer.mouseDoubleClickSequence(preview, p.x, p.y + 20, Qt.LeftButton, Qt.NoModifier, -1)
    if (root.picks.join() !== "1:3,1:4,open") { console.error("FAIL clicks in the preview gave", root.picks.join()); Qt.exit(1); return }
    // Another folder under the resting pointer: new columns all sit at x 0 until the Row places them.
    pointer.mouseMove(preview, p.x, p.y, -1, Qt.NoButton, Qt.NoModifier)
    root.entries = root.entries.map(e => ({ name: "f" + e.name, path: "/t/f" + e.name, isDir: false, size: 1, modified: null }))
    swapped.start()
  } }
  Timer { id: swapped; interval: 100; onTriggered: {
    var column = root.find(c => c.text === root.dirColumns[1])[0], p = column.mapToItem(preview, 10, 3 * 20 + 10)
    var tint = root.find(c => c.line !== undefined && c.column !== undefined && c.visible)[0]
    if (!tint || tint.column !== column || tint.line !== 3) { console.error("FAIL a folder under the pointer tinted the wrong entry"); Qt.exit(1); return }
    pointer.mouseClick(preview, p.x, p.y, Qt.LeftButton, Qt.NoModifier, -1)
    if (root.picks.join() !== "1:3,1:4,open,1:3") { console.error("FAIL a click on a folder under the pointer gave", root.picks.join()); Qt.exit(1); return }
    // A right-click on an entry is that entry's menu, with nothing picked or entered; off the entries,
    // the selection's.
    root.picks = []
    pointer.mouseMove(preview, p.x, p.y, -1, Qt.NoButton, Qt.NoModifier)
    pointer.mouseClick(preview, p.x, p.y, Qt.RightButton, Qt.NoModifier, -1)
    pointer.mouseMove(preview, 2, 2, -1, Qt.NoButton, Qt.NoModifier)
    pointer.mouseClick(preview, 2, 2, Qt.RightButton, Qt.NoModifier, -1)
    if (root.picks.join() !== "menu " + root.previewEntry(1, 3).name + ",menu the folder") {
      console.error("FAIL right-clicks in the preview gave", root.picks.join()); Qt.exit(1); return
    }
    pointer.mouseWheel(preview, p.x, p.y, Qt.NoButton, Qt.NoModifier, 0, -120, -1)
    scrolled.start()
  } }
  Timer { id: scrolled; interval: 300; onTriggered: {
    if (!(root.find(c => c.flickableDirection !== undefined)[0].contentY > 0)) { console.error("FAIL the wheel did not scroll the preview"); Qt.exit(1); return }
    console.log("PASS"); Qt.quit()
  } }
''')

    # A landing far down the list scrolls the real list to it once the new rows are in.
    run("land-scrolls", '''
  property var rows: [{ name: "a", isDir: false, size: 0 }]
  property int index: 0
  property int rowHeight: 30
  property string pending: ""
  property string naming: ""
  property bool editing: false
  property string doomed: ""
  property var changes: ({})
  property color activeFill: "blue"
  property color hoverFill: "gray"
  property color danger: "red"
  property var menu: ({ open: false })
  property var marked: ({})
''' + block(files, r"  function claimPending\(") + block(files, r"  onRowsChanged: \{") + '''
  Window { width: 400; height: 300; visible: true; FilesList { id: list; anchors.fill: parent; panel: root } }
  Timer { interval: 100; running: true; onTriggered: {
    root.pending = "b150"; root.index = -1
    root.rows = Array.from({ length: 200 }, (_, i) => ({ name: "b" + i, isDir: false, size: 0 }))
    landed.start()
  } }
  Timer { id: landed; interval: 100; onTriggered: {
    var row = list.view.itemAtIndex(150)
    if (root.index !== 150 || !row || row.y < list.view.contentY || row.y + row.height > list.view.contentY + list.view.height) {
      console.error("FAIL a landing on row 150 left the list at", list.view.contentY); Qt.exit(1); return
    }
    console.log("PASS"); Qt.quit()
  } }
''')

    # The real menu under real pointer events: a right-click selects its row and opens the menu at the
    # pointer, the probe fills Open with and Taildrop, a click on a row runs it, below the rows opens
    # the folder's own menu, a click outside only closes it, and Ctrl+click marks. A submenu opens
    # beside its row without rebuilding the menu, closes on a second click, and opens on reaching its
    # row while the pointer still moves. gio and tailscale are stand-ins, so the probe reads neither
    # this machine's apps nor its tailnet.
    (base / "gio").write_text(r'''#!/bin/sh
case "$1" in
info) echo "  standard::content-type: text/plain" ;;
mime) printf 'Default application for "text/plain": nvim.desktop\nRegistered applications:\n\tnvim.desktop\n\tomawrite.desktop\n' ;;
esac
''')
    (base / "tailscale").write_text("#!/bin/sh\nprintf '100.1.1.1\\tlaptop\\n100.1.1.2\\tphone\\toffline; last seen 1h ago\\n'\n")
    for name in ["gio", "tailscale"]:
        (base / name).chmod(0o755)
    run("menu-pointer", '''
  property var listedEntries: ["a.txt", "b.txt", "c.txt", "d.txt"].map(n => ({ name: n, path: "/t/" + n, isDir: false, size: 1, modified: null }))
  property var rows: root.listedEntries
  property int index: 0
  readonly property var sel: root.index >= 0 && root.index < root.rows.length ? root.rows[root.index] : null
  property var settledSel: null
  property int rowHeight: 30
  property string pending: ""
  property string naming: ""
  property bool editing: false
  property string doomed: ""
  property var changes: ({})
  property color activeFill: "blue"
  property color hoverFill: "gray"
  property color danger: "red"
  property color edge: "gray"
  property string listedDir: "/t"
  property var held: null
  property bool editable: false
  property string fullText: ""
  property bool showHidden: false
  property string order: "name"
  property bool windowed: false
  property var host: null
  property bool shown: true
  property alias menu: menu
  property var mainMenu: null
  property var subMenu: null
  property var calls: []
  property var marked: ({})
  function settleNow() { root.settledSel = root.sel }
''' + re.search(r"^  readonly property var marks:.*$", files, re.M).group() + "\n" + block(files, r"  readonly property int hiddenMarks:") + block(files, r"  function mark\(") + '''
  QtObject {
    id: ops
    property string doomed: ""
    function activate(e) { root.calls.push("open " + e.name) }
''' + re.search(r"^  function label\(.*$", ops, re.M).group() + '''
  }
  Pointer { id: pointer }
  Window {
    id: window; width: 700; height: 900; visible: true
    FilesList { id: list; width: 300; height: parent.height; panel: root }
    FilesMenu { id: menu; anchors.fill: parent; panel: root; ops: ops; list: list.view }
  }
  function find(test) { var out = [], walk = item => item.children.forEach(c => { if (test(c)) out.push(c); walk(c) }); walk(window.contentItem); return out }
  function cards() { var out = []; menu.children.forEach(c => { if (c.borderSpec !== undefined && c.visible) out.push(c) }); return out }
  function at(text) { var t = root.find(c => c.text === text && c.visible)[0]; return t ? t.mapToItem(window.contentItem, 5, t.height / 2) : null }
  function fail(message) { console.error("FAIL", message); Qt.exit(1) }
  function rightClick(x, y) {
    pointer.mousePress(list, x, y, Qt.RightButton, Qt.NoModifier, -1)
    pointer.mouseRelease(list, x, y, Qt.RightButton, Qt.NoModifier, -1)
  }
  function click(p) { pointer.mouseClick(window.contentItem, p.x, p.y, Qt.LeftButton, Qt.NoModifier, -1) }
  Timer { interval: 200; running: true; onTriggered: {
    root.rightClick(40, 2 * 30 + 15)
    if (root.index !== 2 || !menu.open || !menu.entry || menu.entry.name !== "c.txt") return root.fail("a right-click did not select its row and open its menu")
    var card = root.cards()[0]
    if (!card || Math.abs(card.x - 40) > 1 || Math.abs(card.y - 75) > 1) return root.fail("the menu did not open at the pointer")
    if (root.settledSel !== root.sel) return root.fail("the menu's row did not settle at once")
    probed.start()
  } }
  Timer { id: probed; interval: 400; onTriggered: {
    var apps = menu.context.apps
    if (!apps || apps.map(a => a.id).join() !== "nvim,omawrite" || menu.context.peers.join() !== "laptop")
      return root.fail("the probe gave " + JSON.stringify(menu.probe))
    root.click(root.at("Open"))
    if (root.calls.join() !== "open c.txt" || menu.open) return root.fail("clicking Open gave " + root.calls.join())
    root.rightClick(40, 350)
    if (!menu.open || menu.entry !== null || !menu.rows.some(r => r.id === "new")) return root.fail("below the rows did not open the folder's menu")
    pointer.mouseClick(window.contentItem, 690, 10, Qt.LeftButton, Qt.NoModifier, -1)
    if (menu.open || root.calls.length !== 1) return root.fail("a click outside the menu did more than close it")
    // Ctrl+click marks; a right-click on a mark opens the marks' menu, on any other row that row's.
    pointer.mouseClick(list, 40, 15, Qt.LeftButton, Qt.ControlModifier, -1)
    pointer.mouseClick(list, 40, 45, Qt.LeftButton, Qt.ControlModifier, -1)
    if (root.marks.map(e => e.name).join() !== "a.txt,b.txt") return root.fail("ctrl+click marked " + root.marks.map(e => e.name))
    root.rightClick(40, 45)
    if (!menu.open || !menu.many || menu.many.length !== 2 || menu.rows[0].label !== "2 items")
      return root.fail("a right-click on a mark did not open the marks' menu")
    pointer.mouseClick(window.contentItem, 690, 10, Qt.LeftButton, Qt.NoModifier, -1)
    root.rightClick(40, 3 * 30 + 15)
    if (!menu.open || menu.many || !menu.entry || menu.entry.name !== "d.txt")
      return root.fail("a right-click on an unmarked row did not open its own menu")
    drawn.start()
  } }
  // A frame later, as a person's click would be: the rows are placed when the frame is drawn.
  Timer { id: drawn; interval: 50; onTriggered: {
    // A submenu opens beside its row, level with it, and the menu it came from stays: the same rows,
    // not rebuilt ones.
    var share = root.at("Share"), cut = root.find(c => c.text === "Cut" && c.visible)[0]
    root.click(share)
    var shown = root.cards(), first = root.at("LocalSend…")
    root.mainMenu = shown[0]; root.subMenu = shown[1]
    if (shown.length !== 2 || menu.submenu !== "share" || shown[1].x < shown[0].x + shown[0].width / 2
        || !first || Math.abs(first.y - share.y) > 1)
      return root.fail("a click on Share did not open its menu beside it: " + JSON.stringify([shown.length, menu.submenu, first, share]))
    if (root.find(c => c.text === "Cut" && c.visible)[0] !== cut) return root.fail("opening a submenu rebuilt the menu it came from")
    // A second click on the row closes its submenu, which stays closed while the pointer stays on the row.
    root.click(share)
    if (menu.submenu || root.cards().length !== 1) return root.fail("a second click on Share left its submenu open")
    pointer.mouseMove(window.contentItem, share.x + 3, share.y, -1, Qt.NoButton, Qt.NoModifier)
    pointer.mouseMove(window.contentItem, share.x + 6, share.y, -1, Qt.NoButton, Qt.NoModifier)
    shut.start()
  } }
  Timer { id: shut; interval: 300; onTriggered: {
    if (!menu.open || menu.submenu) return root.fail("a submenu closed by a click reopened under the pointer")
    root.click(root.at("Share"))
    if (menu.submenu !== "share") return root.fail("a third click on Share did not open it")
    // Resting on another row of the menu further out switches to that row's submenu, timed from
    // reaching the row: a pointer still moving within it does not hold it off.
    var pack = root.at("Compress")
    pointer.mouseMove(window.contentItem, pack.x, pack.y, -1, Qt.NoButton, Qt.NoModifier)
    pointer.mouseMove(window.contentItem, pack.x + 2, pack.y, -1, Qt.NoButton, Qt.NoModifier)
    jiggle.at = pack; jiggle.start(); rested.start()
  } }
  Timer { id: jiggle; property var at: null; property int n: 0; interval: 30; repeat: true
    onTriggered: { jiggle.n++; pointer.mouseMove(window.contentItem, jiggle.at.x + 2 + jiggle.n % 2, jiggle.at.y, -1, Qt.NoButton, Qt.NoModifier) } }
  Timer { id: rested; interval: 300; onTriggered: {
    jiggle.stop()
    if (menu.submenu !== "compress" || root.cards().length !== 2)
      return root.fail("a pointer moving on Compress gave " + menu.submenu)
    // ← closes only the submenu, onto the row that holds it.
    menu.back()
    if (menu.submenu || root.cards().length !== 1 || menu.current !== "compress")
      return root.fail("← did not close just the submenu")
    // The keyboard reopens onto the first choice and wraps within the submenu.
    menu.fire(null, true)
    if (menu.current !== "pack.zip") return root.fail("Right did not enter the submenu's first row")
    menu.step(-1)
    if (menu.current !== "pack.tar.zst") return root.fail("Up did not wrap in the submenu")
    menu.back(); menu.current = "with"; menu.fire()
    menu.probe = { apps: ["nvim", "omawrite", "imv"], preferred: "nvim", peers: [], executable: false }
    if (menu.rows.length !== 3) return root.fail("the probe did not fill the open submenu")
    menu.step(Infinity)
    if (menu.current !== "with:imv") return root.fail("End did not reach the probe's new row")
    if (root.cards()[0] !== root.mainMenu || root.cards()[1] !== root.subMenu)
      return root.fail("switching submenus rebuilt a card")
    menu.back(); menu.back()
    if (menu.open) return root.fail("Back from the main menu did not close it")
    window.height = 300
    menu.show(Qt.point(0, 0), root.sel, false)
    geometry.start()
  } }
  Timer { id: geometry; interval: 200; onTriggered: {
    // Both cards fit at each corner, with only the deliberate overlap at their shared edge.
    for (var x of [0, window.width]) for (var y of [0, window.height]) {
      menu.at = Qt.point(x, y)
      for (var row of menu.topRows.filter(r => r.sub)) {
        menu.openSub(row.id, true)
        var cards = root.cards(), a = cards[0], b = cards[1]
        for (var c of cards)
          if (c.x < 0 || c.y < 0 || c.x + c.width > menu.width || c.y + c.height > menu.height)
            return root.fail("a menu left the window at " + [x, y, row.id])
        if (Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x) > a.margin + 1)
          return root.fail("a submenu covered its parent at " + [x, y, row.id])
        menu.back()
      }
    }
    menu.probe = { apps: Array.from({length: 30}, (_, i) => "test-app-" + i), preferred: "", peers: [], executable: false }
    menu.openSub("with", true); menu.step(Infinity)
    var view = root.subMenu.children.find(c => c.contentY !== undefined)
    if (view.contentY <= 0) return root.fail("End did not scroll a tall submenu")
    // Resting on the already-open parent must not reopen it and lose its scroll or highlight.
    menu.hover(menu.topRows.find(r => r.id === "with"), false)
    stayed.start()
  } }
  Timer { id: stayed; interval: 200; onTriggered: {
    if (menu.current !== "with:test-app-29") return root.fail("hovering the open submenu's parent reset it")
    menu.openSub("share", true)
    var view = root.subMenu.children.find(c => c.contentY !== undefined)
    if (view.contentY !== 0) return root.fail("switching submenus retained the old scroll")
    menu.openSub("with", true)
    menu.probe = { apps: [], preferred: "", peers: [], executable: false }
    if (menu.submenu || root.cards().length !== 1) return root.fail("an empty submenu stayed open after the probe")
    menu.close()
    // Filtering keeps marks and names hidden targets; disappearing or unmarked targets close the menu.
    root.rows = root.listedEntries.slice(0, 1)
    menu.openHere()
    if (!menu.many || menu.topRows[0].label !== "2 items (1 hidden)") return root.fail("the marks menu hid its filtered target count")
    ops.doomed = "/t/a.txt\\n/t/b.txt"
    root.listedEntries = root.listedEntries.filter(e => e.name !== "b.txt")
    if (menu.open || ops.doomed || root.marks.length !== 1) return root.fail("a marks menu or armed Trash outlived its targets")
    menu.openHere(); root.marked = ({})
    if (menu.open) return root.fail("an unmarked target kept its marks menu open")
    console.log("PASS"); Qt.quit()
  } }
''', {"PATH": str(base) + ":" + os.environ["PATH"]})

    # Replace the external clipboard owner, preserving the actual shell pipeline
    # and QML completion handler. Nothing touches the desktop clipboard.
    (base / "wl-copy").write_text('#!/bin/sh\ncat > "$CHECK_COPY"\nexit "$CHECK_COPY_EXIT"\n')
    (base / "wl-copy").chmod(0o755)
    captured = base / "clipboard"
    selected = "/home/test/a '$file with spaces.txt"
    clipboard = '''
  // FilesOps borrows the selection from its panel; here it is its own.
  property var panel: root
  property bool editing: false
  property string home: "/home/test"
  property var sel: ({path: ''' + json.dumps(selected) + '''})
  property var op: null
  property string fileNote: ""
  property bool cancelling: false
  property real progress: -1
  property int elapsed: 0
  function note(text) { root.fileNote = text }
''' + block(ops, r"  function run\(") + block(ops, r"  function copyPath\(") + block(ops, r"  Process {\n    id: filer") + block(ops, r"  Process {\n    id: gauge") + '''
  Component.onCompleted: {
    root.copyPath([root.sel])
    if (root.fileNote) { console.error("FAIL premature success"); Qt.exit(1) }
  }
  onFileNoteChanged: {
    var failed = Quickshell.env("CHECK_COPY_EXIT") !== "0"
    if (failed ? root.fileNote !== "copy path failed" : root.fileNote.indexOf("copied ") !== 0) {
      console.error("FAIL completion", root.fileNote); Qt.exit(1)
    } else { console.log("PASS"); Qt.quit() }
  }
'''
    for code in [0, 127]:
        run("clipboard-" + str(code), clipboard,
            {"PATH": str(base) + ":" + os.environ["PATH"], "CHECK_COPY": str(captured),
             "CHECK_COPY_EXIT": str(code)})
        assert captured.read_text() == selected

    # A long note, then a running job, stand in for the selection's facts beside a path: neither runs over
    # the path, and the job's progress is never the part cut short. A note shows with nothing selected.
    run("header-note", '''
  property string note: "copying PrintShop-Tools-Windows-x64-phase1-with-an-even-longer-name.zip"
  property bool job: false
  property bool empty: false
  QtObject {
    id: panel
    property var crumbs: ["~", "Downloads", "agent-test-folder"]
    property bool pathMode: false
    property string typedLeaf: ""
    property string naming: ""
    property string filter: ""
    property string renameTo: ""
    property int renameAt: 0
    property bool editing: false
    property var settledSel: root.empty ? null : ({ name: "PrintShop-Tools-Windows-x64-phase1.zip" })
    property string fileNote: root.note
    property string fileStatusHead: root.job ? "extracting PrintShop-Tools-Windows-x64-phase1-with-an-even-longer-name.zip" : ""
    property string fileStatusTail: root.job ? " · 1:20 · ctrl+k cancels" : ""
    property string filePercent: root.job ? "42%" : ""
    property real fileProgress: root.job ? 0.42 : -1
    property string diffText: ""
    property real previewWidth: 480
    property string metaLine: "93.7 MB · 2 days ago"
    property var rows: [1, 2, 3]
    property var listedEntries: [1, 2, 3]
    property string query: ""
    property bool showHidden: false
    property string order: "name"
    property var marks: []
    property int hiddenMarks: 0
    property bool shown: true
    property bool saveError: false
    property bool justSaved: false
    property bool dirty: false
    property var menu: null
  }
  FloatingWindow {
    visible: true; implicitWidth: 800; implicitHeight: 50
    FilesHeader { id: header; width: 800; panel: panel }
  }
  function clear() {
    var trail = header.children.find(c => c.spacing !== undefined && c.anchors.left === header.left)
    var facts = header.children.find(c => c.spacing !== undefined && c.anchors.right === header.right)
    return facts.x >= trail.x + trail.width
  }
  function find(item, test) {
    if (test(item)) return item
    for (var i = 0; i < item.children.length; i++) { var f = find(item.children[i], test); if (f) return f }
    return null
  }
  Timer { interval: 200; running: true; onTriggered: {
    if (!root.clear()) return root.fail("a note ran over the path")
    root.note = ""; root.job = true; later.start()
  } }
  Timer { id: later; interval: 200; onTriggered: {
    var progress = root.find(header, c => c.text !== undefined && c.text.indexOf("42%") >= 0)
    if (!root.clear()) return root.fail("a running job ran over the path")
    if (!progress || !progress.visible || progress.width < progress.implicitWidth) return root.fail("the job's progress was cut")
    root.job = false; root.empty = true; root.note = "trashed 3 items"; emptied.start()
  } }
  // Trashing a folder's last leaves nothing selected; the note still shows.
  Timer { id: emptied; interval: 200; onTriggered: {
    var note = root.find(header, c => c.text === "trashed 3 items")
    if (!note || !note.visible) return root.fail("a note in an empty folder was hidden")
    console.log("PASS"); Qt.quit()
  } }
  function fail(why) { console.error("FAIL", why); Qt.exit(1) }
''', expected=(r"does not support setting window masks",))

    # Qt's FolderListModel lists the parent for "#archive" and "50%25off", and a fresh one the working directory
    # for "q?x" or a gone folder; the panel shows none of those rows. An unreadable folder lists as
    # empty, so it, and the gone one, say they can't be listed.
    for name in ["#archive", "q?x", "50%25off", "plain"]:
        (base / "listing" / name).mkdir(parents=True)
        (base / "listing" / name / "inside").touch()
    (base / "listing/locked").mkdir(mode=0)
    listing = '''
  property bool showHidden: false
  property string listedDir: ""
  property var entries: []
  property var dirs: ''' + json.dumps([str(base / "listing" / n) for n in ["#archive", "q?x", "50%25off", "gone", "plain", "locked"]]) + '''
  property var seen: []
  onListedDirChanged: root.checkAccess(root.listedDir)
''' + block(files, r"  FolderListModel \{\n    id: listedFolder") + re.search(r"  readonly property bool unlisted:.*?  FilesProcess \{ id: access.*?\n", files, re.S).group() + '''
  Timer { interval: 300; running: true; repeat: true; onTriggered: {
    if (root.listedDir) root.seen.push(JSON.stringify([root.entries.map(e => e.path), root.unlisted]))
    if (root.seen.length < root.dirs.length) { root.listedDir = root.dirs[root.seen.length]; return }
    // A reused model reports nothing for ? and a gone folder; "#archive" and "%25" list the parent, caught.
    var want = [[[], true], [[], false], [[], false], [[], true], [[root.dirs[4] + "/inside"], false], [[], true]].map(s => JSON.stringify(s))
    if (JSON.stringify(root.seen) !== JSON.stringify(want)) { console.error("FAIL", JSON.stringify(root.seen)); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
'''
    run("files-lists-only-its-folder", listing, expected=(r"QFileSystemWatcher::removePath: path is empty$",
                                                          r"inotify_add_watch\(.*/locked\) failed: \(Permission denied\)$"))

    # A folder selected again, as when the list reloads around it, keeps its preview: its model does
    # not change folder, so nothing would refill it. Another folder with as many entries still fills in.
    # So does a folder's only folder, entered from it, as /mnt's server-storage is.
    for name in ["one", "two"]:
        (base / "reselect" / name).mkdir(parents=True)
        (base / "reselect" / name / ("in-" + name)).touch()
    (base / "reselect/deep/in-deep").mkdir(parents=True)
    (base / "reselect/deep/in-deep/in-in-deep").touch()
    reselect = '''
  property bool showHidden: false
  property bool showsImage: false
  property int shownLines: 0
  property string diffText: ""
  property string imageDims: ""
  property string unreadable: ""
  property string settledPath: ""
  property var settledSel: null
  property var dirEntries: []
  readonly property int dirLimit: 400
  property var dirs: ''' + json.dumps([str(base / "reselect" / n) for n in ["one", "one", "two", "deep", "deep/in-deep"]]) + '''
  property var seen: []
  function readDiff() {}
  function checkAccess(dir) {}
  QtObject { id: preview; property int paneHeight: 100; function resetScroll() {} }
  QtObject { id: measurer; function cancel() {} }
  property bool props: false
  property string folderSize: ""
  QtObject { id: sizer; property var sizes: ({}); function cancel() {} function start(command) {} }
''' + "\n".join([block(files, r"^  function media\("), block(files, r"^  onSettledSelChanged: \{").replace("Style.font.subtitle", "16"),
                 block(files, r"  FolderListModel \{\n    id: childFolder"),
                 block(files, r"^  readonly property bool childUnlisted:")]) + '''
  Timer { interval: 300; running: true; repeat: true; onTriggered: {
    if (root.settledSel) root.seen.push(JSON.stringify([root.dirEntries.map(e => e.path), root.childUnlisted]))
    if (root.seen.length < root.dirs.length) {
      var dir = root.dirs[root.seen.length]
      root.settledSel = { path: dir, name: dir.split("/").pop(), isDir: true }
      return
    }
    var want = root.dirs.map(d => JSON.stringify([[d + "/in-" + d.split("/").pop()], false]))
    if (JSON.stringify(root.seen) !== JSON.stringify(want)) { console.error("FAIL", JSON.stringify(root.seen)); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
'''
    run("files-reselect-keeps-preview", reselect, expected=(r"QFileSystemWatcher::removePath: path is empty$",))

    # A folder still listing, as a network share mounting, holds the last folder's rows: neither pane
    # says it can't be listed until the listing is in.
    note = files[files.index("  readonly property string previewNote:"):files.index("  // Payloads may choose")]
    run("files-loading-is-not-unlistable", '''
  property bool editing: false
  property var settledSel: null
  property string pending: ""
  property bool unlisted: true
  property bool childUnlisted: true
  property bool showsDir: false
  QtObject { id: listedFolder; property int status: FolderListModel.Loading }
  QtObject { id: childFolder; property int status: FolderListModel.Loading }
''' + note + '''
  Timer { interval: 0; running: true; onTriggered: {
    var seen = [previewNote]
    settledSel = { isDir: true, name: "share", path: "/mnt/share" }
    seen.push(previewNote)
    listedFolder.status = childFolder.status = FolderListModel.Ready
    seen.push(previewNote)
    settledSel = null
    seen.push(previewNote)
    var want = ["", "", "Can't list this folder", "Can't list this folder"]
    if (JSON.stringify(seen) !== JSON.stringify(want)) { console.error("FAIL", JSON.stringify(seen)); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')
