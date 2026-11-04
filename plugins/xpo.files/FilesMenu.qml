pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "FilesActions.js" as FilesActions
import "FilesIndex.js" as FilesIndex

// The right-click menu. Drawn inside the browser rather than as a popup of its own, so it goes with
// the browser into its window or the pinned search, and the keyboard never leaves the panel. It acts
// on the row it opened on, which the panel keeps selected while it is open, or on the marks. A
// submenu opens beside the row that holds it, and the menus it came from stay open.
Item {
  id: root

  property var panel: null
  property var ops: null
  // The list, so the keyboard can open the menu under its selected row.
  property var list: null

  property bool open: false
  // The row it opened on, or null for the folder's own menu; or else the marks it acts on.
  property var entry: null
  property var many: null
  readonly property var targets: root.many || (root.entry ? [root.entry] : [])
  // What the probe learned of the row, or null until it answers.
  property var probe: null
  // The submenus open, outermost first: each the id of the row that holds it, and where it opens.
  property var stack: []
  // The highlighted row's id, in the innermost menu open.
  property string current: ""
  property point at: Qt.point(0, 0)

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
      doomed: root.armed,
      showHidden: p.showHidden, order: p.order, popped: p.windowed || !!p.host
    }
  }
  readonly property var topRows: root.open ? FilesActions.tree(root.context) : []
  // Each menu open, outermost first, with where it opens. Found by id each time, so a submenu fills
  // in when the probe answers.
  readonly property var levels: {
    var out = [{ rows: root.topRows, x: root.at.x, y: root.at.y, left: 0 }]
    for (var i = 0; i < root.stack.length; i++) {
      var node = out[i].rows.find(r => r.id === root.stack[i].id)
      if (!node || !node.sub) break
      out.push({ rows: node.sub, x: root.stack[i].x, y: root.stack[i].y, left: root.stack[i].left })
    }
    return out
  }
  // The innermost menu, which the keyboard moves through.
  readonly property int depth: root.levels.length - 1
  readonly property var rows: root.levels[root.depth].rows
  readonly property var choices: root.rows.filter(r => !r.sep && !r.off)
  // Trash is armed for exactly what the menu acts on: its paths, joined as FilesOps arms them.
  readonly property bool armed: root.open && root.targets.length > 0
                                && root.panel.doomed === root.targets.map(t => t.path).join("\n")

  // A card for each menu open, kept while it stays open: a submenu opening adds a card rather than
  // rebuilding the cards already open.
  ListModel { id: slots }
  function fitSlots() {
    while (slots.count < root.levels.length) slots.append({ n: slots.count })
    if (slots.count > root.levels.length) slots.remove(root.levels.length, slots.count - root.levels.length)
  }
  onLevelsChanged: root.fitSlots()

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
    root.probe = null
    root.stack = []
    root.shut = ""
    root.at = point
    root.open = true
    root.current = keyboard ? root.firstChoice() : ""
    gate.reset()
    // The menu shows what the preview knows of its row, so that should not wait out the debounce.
    if (root.entry) root.panel.settleNow()
    var first = root.targets[0]
    if (first && !first.missing) prober.start(["sh", "-c", FilesActions.PROBE, "files", first.path])
  }
  function close() {
    if (!root.open) return
    soon.stop()
    root.open = false
    root.entry = null
    root.many = null
    root.stack = []
    prober.cancel()
    root.ops.doomed = ""
  }

  function firstChoice() { return root.choices.length ? root.choices[0].id : "" }
  // The arrows wrap; any longer step goes to that end.
  function step(d) {
    var ids = root.choices.map(r => r.id), i = ids.indexOf(root.current)
    if (!ids.length) return
    if (Math.abs(d) !== 1) i = d < 0 ? 0 : ids.length - 1
    else i = i < 0 ? (d > 0 ? 0 : ids.length - 1) : (i + d + ids.length) % ids.length
    root.current = ids[i]
    gate.reset()
    cards.itemAt(root.depth).reveal(root.current)
  }
  // The submenu of row id, in the menu at depth, opened beside that row and closing any opened
  // from further in; from the keyboard, onto its first row.
  function openSub(depth, id, keyboard) {
    soon.stop()
    root.stack = root.stack.slice(0, depth).concat([cards.itemAt(depth).beside(id)])
    root.current = keyboard ? root.firstChoice() : ""
    gate.reset()
  }
  // A click on a row of the menu at depth, or Enter or → (into only) on the highlighted row: its
  // submenu opens, or it runs. A row that returns true keeps the menu open.
  function fire(row, into, depth) {
    var keyboard = depth === undefined
    row = row || root.choices.find(r => r.id === root.current)
    if (!row || row.sep || row.off || (into && !row.sub)) return
    if (!row.sub) { if (!row.run()) root.close(); return }
    // A second click on the row of an open submenu closes it, and it stays closed while the pointer
    // stays on the row.
    if (!keyboard && depth < root.depth && root.stack[depth].id === row.id) {
      soon.stop()
      root.stack = root.stack.slice(0, depth)
      root.current = row.id
      root.shut = depth + ":" + row.id
      return
    }
    root.openSub(keyboard ? root.depth : depth, row.id, keyboard)
  }
  // Out of the innermost submenu onto the row that holds it; out of the menu from the top.
  function back() {
    soon.stop()
    if (!root.stack.length) { root.close(); return }
    root.current = root.stack[root.stack.length - 1].id
    root.stack = root.stack.slice(0, -1)
    gate.reset()
  }
  // Del with Trash armed confirms it, wherever the highlight is.
  function confirm() {
    var trash = root.topRows.find(r => r.id === "trash")
    if (trash) root.fire(trash, false, 0)
  }

  // The pointer highlights a row of the innermost menu, and resting on one that holds a submenu opens
  // it, as desktop menus do. Back on a menu further out it switches after the same rest, so a pointer
  // crossing that menu's rows on its way into a submenu leaves the submenu open.
  property string shut: ""
  function hover(depth, row) {
    var shut = root.shut === depth + ":" + row.id
    if (!shut) root.shut = ""
    if (depth === root.depth) {
      root.current = row.id
      if (row.sub && !shut) soon.wait(depth, row.id)
      else soon.stop()
    } else if (root.stack[depth].id !== row.id) soon.wait(depth, row.id)
    else soon.stop()
  }
  // The rest is timed from reaching the row: the pointer still moving within it does not hold it off.
  Timer {
    id: soon
    interval: 150
    property int depth: 0
    property string row: ""
    function wait(depth, row) {
      if (soon.running && soon.depth === depth && soon.row === row) return
      soon.depth = depth
      soon.row = row
      soon.restart()
    }
    onTriggered: {
      var row = (root.levels[soon.depth] || { rows: [] }).rows.find(x => x.id === soon.row)
      if (!row) return
      if (row.sub) root.openSub(soon.depth, row.id, false)
      else { root.stack = root.stack.slice(0, soon.depth); root.current = row.id }
    }
  }

  Connections {
    target: root.panel
    function onShownChanged() { if (!root.panel.shown) root.close() }
    function onListedDirChanged() { root.close() }
    function onNamingChanged() { if (root.panel.naming) root.close() }
  }

  FilesProcess {
    id: prober
    onFinished: output => root.probe = FilesActions.readProbe(output)
  }

  PointerMoveGate { id: gate; referenceItem: root }

  TextMetrics {
    id: metrics
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.body
    text: "0"
  }

  // Anywhere outside the menus closes them, and nothing beneath takes the click or the wheel.
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.AllButtons
    onPressed: root.close()
    onWheel: wheel => wheel.accepted = true
  }

  Repeater {
    id: cards
    model: slots

    delegate: BorderSurface {
      id: card
      required property int index
      readonly property var level: root.levels[card.index] || { rows: [], x: 0, y: 0, left: 0 }
      readonly property var rows: card.level.rows
      readonly property int margin: Style.spacing.sm

      width: Math.min(root.width - margin * 2, Math.round(metrics.advanceWidth * 36) + Style.spacing.rowPaddingX * 2)
      height: Math.min(root.height - margin * 2, column.height + Style.spacing.sm * 2)
      // The menu opens at the pointer. A submenu opens beside its row, over the edge of the menu it
      // came from so no gap lies between them, its first row level with that row; and on the other
      // side of that menu when there is no room on this one.
      x: !card.index ? Math.max(margin, Math.min(card.level.x, root.width - width - margin))
         : card.level.x - Style.spacing.sm + width <= root.width - margin ? card.level.x - Style.spacing.sm
         : Math.max(margin, card.level.left - width + Style.spacing.sm)
      y: Math.max(margin, Math.min(card.level.y - (card.index ? Style.spacing.sm : 0), root.height - height - margin))
      radius: Style.space(16)
      color: Util.alpha(Commons.Color.menu.background, 0.98)
      borderSpec: Border.flat(root.panel.edge, Style.spacing.hairline)

      // The column places its rows when the frame is drawn, and a key can come first.
      function rowItem(id) {
        column.forceLayout()
        return lines.itemAt(card.rows.findIndex(r => r.id === id))
      }
      // Where the submenu of row id opens: past this menu's right edge, level with the row.
      function beside(id) {
        var row = card.rowItem(id)
        return { id: id, x: card.x + card.width, y: row ? row.mapToItem(root, 0, 0).y : card.y, left: card.x }
      }
      // Scrolls a menu taller than the browser to the row the keyboard reached.
      function reveal(id) {
        var row = card.rowItem(id)
        if (!row) return
        if (row.y < view.contentY) view.contentY = row.y
        else if (row.y + row.height > view.contentY + view.height) view.contentY = row.y + row.height - view.height
      }

      // A click between rows stays in the menu, and the pointer reaching a submenu keeps it open.
      MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.AllButtons
        hoverEnabled: true
        onPositionChanged: if (card.index > soon.depth) soon.stop()
      }

      // Every row built at once, not as a ListView builds them, a screen at a time: the card takes
      // its height from its rows, so a ListView inside it would start a row tall and grow by frames.
      Flickable {
        id: view
        anchors.fill: parent
        anchors.margins: Style.spacing.sm
        clip: true
        contentHeight: column.height
        interactive: contentHeight > height
        boundsBehavior: Flickable.StopAtBounds

        Column {
          id: column
          width: view.width

          Repeater {
            id: lines
            // A count, not the rows: an array handed over again rebuilds every row, and every
            // submenu that opens or closes hands each menu its rows again.
            model: card.rows.length

            delegate: Item {
              id: line
              required property int index
              readonly property var modelData: card.rows[line.index] || ({})
              // A menu further out keeps lit the row whose submenu is open.
              readonly property bool lit: card.index < root.depth ? root.stack[card.index].id === line.modelData.id
                                                                   : root.current === line.modelData.id
              readonly property bool armedRow: line.modelData.id === "trash" && root.armed

              width: column.width
              height: line.modelData.sep ? Style.spacing.lg : Style.spacing.popupRowHeight

              Rectangle {
                visible: !!line.modelData.sep
                anchors.centerIn: parent
                width: parent.width - Style.spacing.md * 2
                height: Style.spacing.hairline
                color: root.panel.edge
              }

              // The list's selection capsule; Trash fills red once armed, as its row in the list does.
              Rectangle {
                visible: !line.modelData.sep
                anchors.fill: parent
                radius: height / 2
                color: line.armedRow ? Util.alpha(root.panel.danger, 0.30) : line.lit ? root.panel.activeFill
                       : pointer.containsMouse ? root.panel.hoverFill : "transparent"
                border.width: line.lit || line.armedRow ? Style.spacing.hairline : 0
                border.color: line.armedRow ? root.panel.danger : Commons.Color.accent
              }

              Text {
                visible: !line.modelData.sep
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: Style.spacing.rowPaddingX
                anchors.right: hint.left
                anchors.rightMargin: Style.spacing.md
                elide: Text.ElideMiddle
                text: line.modelData.label || ""
                color: line.modelData.danger ? root.panel.danger
                       : line.lit ? Commons.Color.menu.selectedText : Commons.Color.menu.text
                opacity: line.modelData.off ? 0.35 : line.lit || line.modelData.danger ? 1.0 : 0.82
                font.family: Style.font.menuFamily
                font.pixelSize: Style.font.body
              }

              // The key that does the same without the menu, or › for a submenu.
              Text {
                id: hint
                visible: !line.modelData.sep
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: Style.spacing.rowPaddingX
                text: line.modelData.sub ? "›" : line.modelData.hint || ""
                color: line.lit ? Commons.Color.accent : Commons.Color.menu.text
                opacity: line.lit ? 0.75 : 0.45
                font.family: Style.font.menuFamily
                font.pixelSize: line.modelData.sub ? Style.font.body : Style.font.caption
              }

              // Hover counts only once the pointer itself moves, so the rows that open under a resting
              // pointer do not claim it.
              MouseArea {
                id: pointer
                anchors.fill: parent
                enabled: !line.modelData.sep && !line.modelData.off
                hoverEnabled: true
                onPositionChanged: mouse => { if (gate.moved(pointer, mouse)) root.hover(card.index, line.modelData) }
                onClicked: root.fire(line.modelData, false, card.index)
              }
            }
          }
        }
      }
    }
  }
}
