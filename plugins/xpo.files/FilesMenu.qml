pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.Commons
import qs.Ui
import "FilesActions.js" as FilesActions
import "FilesIndex.js" as FilesIndex

// The menu covers the overlay, or stays inside the browser's window or pinned search.
// It acts on its entry (including a preview's child) or the marks without moving keyboard focus.
Item {
  id: root
  property var panel: null
  property var ops: null
  property var list: null
  property bool open: false
  property var entry: null
  property var many: null
  property bool aside: false
  readonly property var targets: root.many || (root.entry ? [root.entry] : [])
  property var probe: null
  property string submenu: ""
  property point subAt: Qt.point(0, 0)
  property string current: ""
  property point at: Qt.point(0, 0)
  property string shut: ""
  readonly property alias pointerGate: gate
  visible: root.open

  readonly property var context: {
    var e = root.entry, p = root.panel, file = !!e && !e.isDir
    var settled = !!e && !!p.settledSel && p.settledSel.path === e.path
    return {
      panel: p, ops: root.ops, entry: e, many: root.many, dir: p.listedDir, held: p.held,
      image: file && FilesIndex.isImage(e.name), video: file && FilesIndex.isVideo(e.name),
      urls: root.targets.map(t => FilesIndex.fileUrl(t.path)),
      editable: settled && p.editable,
      script: file && FilesActions.isScript(e.name, settled ? p.fullText : ""),
      executable: !!root.probe && root.probe.executable,
      apps: root.probe ? root.probe.apps.map(root.app) : null,
      preferred: root.probe ? root.probe.preferred : "",
      peers: root.probe ? root.probe.peers : [],
      doomed: root.armed, hidden: root.many ? p.hiddenMarks : 0,
      showHidden: p.showHidden, order: p.order, popped: p.windowed || !!p.host
    }
  }
  readonly property var topRows: root.open ? FilesActions.tree(root.context) : []
  // Resolve by id so the probe can fill an already-open submenu.
  readonly property var subRows: (root.topRows.find(r => r.id === root.submenu) || {}).sub || []
  readonly property var rows: root.subRows.length ? root.subRows : root.topRows
  readonly property var choices: root.rows.filter(r => !r.sep && !r.off)
  readonly property bool armed: root.open && root.targets.length > 0
                                && root.panel.doomed === root.targets.map(t => t.path).join("\n")
  onTopRowsChanged: if (root.submenu && !root.topRows.some(r => r.id === root.submenu && r.sub)) root.submenu = ""

  function app(id) {
    var e = DesktopEntries.byId(id)
    return { id: id, name: e ? e.name : id, terminal: !!e && e.runInTerminal,
             command: e ? (e.command || []).filter(w => !/^%[a-zA-Z]$/.test(String(w))) : [] }
  }

  // From the pointer: at the point in item, for the row given, or the folder's own menu for none.
  function openAt(item, x, y, entry) { root.show(item.mapToItem(root, x, y), entry, false) }
  // From the keyboard: under the selected row's name, or at the top of an empty list.
  function openHere() {
    var row = root.panel.sel ? root.list.itemAtIndex(root.panel.index) : null
    root.show(row ? row.mapToItem(root, Style.font.iconLarge + Style.spacing.rowPaddingX * 2, row.height)
                  : root.list.mapToItem(root, Style.spacing.rowPaddingX, 0), root.panel.sel, true)
  }
  // The marks make it theirs from the keyboard, or from a right-click on one of them; a right-click
  // on an unmarked row is for that row alone.
  function show(point, entry, keyboard) {
    var marks = root.panel.marks
    root.many = marks.length && (keyboard || (!!entry && !!root.panel.marked[entry.path])) ? marks : null
    root.entry = root.many ? null : entry
    root.aside = !!root.entry && root.entry !== root.panel.sel
    root.probe = null
    root.submenu = ""
    root.shut = ""
    root.at = point
    mainCard.resetScroll()
    root.open = true
    root.current = keyboard ? root.firstChoice() : ""
    gate.reset()
    if (root.entry) root.panel.settleNow()
    var command = FilesActions.probeCommand(root.entry, root.targets)
    if (command.length) prober.start(command)
  }
  function close() {
    if (!root.open) return
    soon.stop()
    root.open = false
    root.entry = null
    root.many = null
    root.submenu = ""
    prober.cancel()
    root.ops.doomed = ""
  }

  function firstChoice() { return root.choices.length ? root.choices[0].id : "" }
  function step(d) {
    var ids = root.choices.map(r => r.id), i = ids.indexOf(root.current)
    if (!ids.length) return
    if (Math.abs(d) !== 1) i = d < 0 ? 0 : ids.length - 1
    else i = i < 0 ? (d > 0 ? 0 : ids.length - 1) : (i + d + ids.length) % ids.length
    root.current = ids[i]
    gate.reset()
    var card = root.submenu ? subCard : mainCard
    card.reveal(root.current)
  }
  function openSub(id, keyboard) {
    soon.stop()
    root.subAt = mainCard.beside(id)
    root.submenu = id
    subCard.resetScroll()
    root.current = keyboard ? root.firstChoice() : ""
    gate.reset()
  }
  // Enter or a click runs a row; Right only opens submenus. A true result keeps the menu open.
  function fire(row, into, pointer) {
    row = row || root.choices.find(r => r.id === root.current)
    if (!row || row.sep || row.off || (into && !row.sub)) return
    if (!row.sub) { if (!row.run()) root.close(); return }
    if (pointer && root.submenu === row.id) {
      root.back()
      root.shut = row.id
    } else root.openSub(row.id, !pointer)
  }
  function back() {
    soon.stop()
    if (!root.submenu) { root.close(); return }
    root.current = root.submenu
    root.submenu = ""
    gate.reset()
  }
  function trash() {
    var row = root.topRows.find(r => r.id === "trash")
    if (row) root.fire(row)
  }
  // Delay switches while crossing the main menu; entering the submenu cancels the switch.
  function hover(row, fromSub) {
    if (fromSub) { soon.stop(); if (row) root.current = row.id; return }
    if (root.shut !== row.id) root.shut = ""
    if (!root.submenu) root.current = row.id
    if (root.submenu ? root.submenu !== row.id : row.sub && root.shut !== row.id) soon.wait(row.id)
    else soon.stop()
  }
  Timer {
    id: soon
    interval: 150
    property string row: ""
    function wait(id) {
      if (soon.running && soon.row === id) return
      soon.row = id
      soon.restart()
    }
    onTriggered: {
      var row = root.topRows.find(r => r.id === soon.row)
      if (!row) return
      if (row.sub) root.openSub(row.id, false)
      else { root.submenu = ""; root.current = row.id }
    }
  }
  Connections {
    target: root.panel
    function onShownChanged() { if (!root.panel.shown) root.close() }
    function onListedDirChanged() { root.close() }
    function onNamingChanged() { if (root.panel.naming) root.close() }
    function onMarksChanged() {
      if (root.many && root.many.map(e => e.path).join("\n") !== root.panel.marks.map(e => e.path).join("\n")) root.close()
    }
  }
  FilesProcess { id: prober; onFinished: output => root.probe = FilesActions.readProbe(output) }
  PointerMoveGate { id: gate; referenceItem: root }
  // Outside clicks close the menu without reaching the browser underneath.
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.AllButtons
    onPressed: root.close()
    onWheel: wheel => wheel.accepted = true
  }
  FilesMenuCard { id: mainCard; menu: root; rows: root.topRows; at: root.at }
  FilesMenuCard {
    id: subCard
    menu: root
    rows: root.subRows
    visible: rows.length > 0
    isSub: true
    at: root.subAt
    parentLeft: mainCard.x
  }
}
