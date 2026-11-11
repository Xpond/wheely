pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import "FilesIndex.js" as FilesIndex

Item {
  id: root
  property var panel: null
  property var operations: null
  property alias view: list

  // A click selects; with Ctrl it also marks or unmarks the row, with Shift it marks from the
  // selection to the row. Never while naming or editing, so the row being renamed or edited stays
  // the one selected.
  function click(i, modifiers) {
    var p = root.panel, row = p.rows[i]
    if (p.naming || p.editing) return
    if (modifiers & Qt.ControlModifier) p.mark([row], !p.marked[row.path])
    else if ((modifiers & Qt.ShiftModifier) && p.sel) p.mark(p.rows.slice(Math.min(p.index, i), Math.max(p.index, i) + 1), true)
    p.pending = ""
    p.index = i
  }

  // A hovered row's name pops up whole over it after a moment, cut short or not. The row is found
  // from where the pointer is, on every move and every scroll, since a scroll moves rows under a
  // still pointer without telling them.
  property Item under: null
  property Item tipped: null
  function rest(moved) {
    var p = pointing.point.position
    var row = pointing.hovered ? list.itemAtIndex(list.indexAt(p.x + list.contentX, p.y + list.contentY)) : null
    var name = row ? row.title : null
    if (name === root.under && !moved) return
    root.under = name
    root.tipped = null
    if (name) tipWait.restart()
  }
  Timer { id: tipWait; interval: 500; onTriggered: root.tipped = root.under }
  // On the list's frame, not in it: a handler in a Flickable rides its content, and its point with it.
  HoverHandler { id: pointing; onPointChanged: root.rest(false); onHoveredChanged: root.rest(false) }

  ListView {
    id: list
    anchors.fill: parent
    clip: true
    // A count, not the rows: the view would copy an array row by row on every change, 127 ms at 100k.
    model: root.panel.rows.length
    currentIndex: root.panel.index
    reuseItems: true
    boundsBehavior: Flickable.StopAtBounds
    onContentYChanged: root.rest(true)

    delegate: Item {
      id: entry
      required property int index
      readonly property var modelData: root.panel.rows[entry.index] || ({ name: "", path: "" })
      readonly property bool active: root.panel.index === entry.index
      // What is armed is a list of paths, one to a line.
      readonly property bool doomed: ("\n" + root.panel.doomed + "\n").indexOf("\n" + entry.modelData.path + "\n") >= 0
      readonly property bool marked: !!root.panel.marked[entry.modelData.path]
      readonly property Item title: label

      width: list.width
      height: root.panel.rowHeight

      // Match the wheel's selection capsule, stopping before the preview.
      Rectangle {
        anchors.fill: parent
        anchors.rightMargin: Style.spacing.md
        radius: height / 2
        color: entry.doomed ? Util.alpha(root.panel.danger, 0.30)
               : entry.active ? root.panel.activeFill
               : entry.marked ? Util.alpha(Commons.Color.accent, 0.08)
               : (pointer.containsMouse ? root.panel.hoverFill : "transparent")
        border.width: entry.active ? Style.spacing.hairline : 0
        border.color: entry.doomed ? root.panel.danger : Commons.Color.accent
      }

      // Hover only tints the row. A click selects and a double click opens, never while naming
      // or editing, so the row being renamed or edited stays the one selected.
      MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        onClicked: mouse => root.click(entry.index, mouse.modifiers)
        onDoubleClicked: if (!root.panel.naming) root.operations.activate(entry.modelData)
      }

      Row {
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: Style.spacing.rowPaddingX
        anchors.right: parent.right
        anchors.rightMargin: Style.spacing.rowPaddingX + Style.spacing.md
        spacing: Style.spacing.controlGap

        // Folder colour remains distinct in a list of files; a mark takes the glyph's place.
        Text {
          id: glyph
          anchors.verticalCenter: parent.verticalCenter
          width: Style.font.iconLarge
          text: entry.marked ? "\u{F012C}" : entry.modelData.isDir ? "󰉋" : "󰈔"
          color: entry.active || entry.marked ? Commons.Color.accent
                 : entry.modelData.isDir ? Util.alpha(Commons.Color.accent, 0.55)
                 : Util.alpha(Commons.Color.menu.text, 0.35)
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.iconLarge
        }

        Text {
          id: label
          anchors.verticalCenter: parent.verticalCenter
          width: parent.width - glyph.width - trail.width - parent.spacing * 2
                 - (mark.visible ? mark.width + parent.spacing : 0)
          elide: Text.ElideRight
          text: entry.modelData.name
          color: entry.active ? Commons.Color.menu.selectedText : Commons.Color.menu.text
          opacity: entry.active ? 1.0 : (entry.modelData.isDir ? 0.88 : 0.66)
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }

        // Uncommitted changes: git's letter on a file, a dot on a folder holding some.
        Text {
          id: mark
          anchors.verticalCenter: parent.verticalCenter
          visible: !!text
          text: root.panel.changes[entry.modelData.name] || ""
          color: Commons.Color.accent
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          id: trail
          anchors.verticalCenter: parent.verticalCenter
          text: entry.modelData.isDir
                ? (entry.active ? "›" : "")
                : FilesIndex.humanSize(entry.modelData.size)
          color: entry.active ? Commons.Color.accent : Commons.Color.menu.text
          opacity: entry.active ? 0.75 : 0.45
          font.family: Style.font.menuFamily
          font.pixelSize: entry.modelData.isDir ? Style.font.body : Style.font.bodySmall
        }
      }
    }
  }

  // New rows start from the top, as a new model did, also when their count is the same.
  Connections { target: root.panel; function onRowsChanged() { list.positionViewAtBeginning() } }

  // A right-click selects its row and opens the menu there, or the folder's own menu below the
  // rows. The right button only: left clicks, hover and the wheel go on to the rows.
  MouseArea {
    anchors.fill: list
    acceptedButtons: Qt.RightButton
    onPressed: mouse => {
      if (root.panel.naming || root.panel.editing) return
      var i = list.indexAt(mouse.x + list.contentX, mouse.y + list.contentY)
      if (i >= 0) root.click(i, 0)
      root.panel.menu.openAt(list, mouse.x, mouse.y, i >= 0 ? root.panel.sel : null)
    }
  }

  // Over the preview too, as far as the pane goes, and wrapped past that.
  FilesTip {
    readonly property point at: root.tipped ? root.tipped.mapToItem(root, 0, 0) : Qt.point(0, 0)
    visible: !!root.tipped
    x: at.x - pad
    y: root.tipped ? at.y + (root.tipped.height - height) / 2 : 0
    maxWidth: root.parent.width - x
    text: root.tipped ? root.tipped.text : ""
    pixelSize: Style.font.body
  }

  // Show the scroll position in long directories.
  Rectangle {
    visible: list.contentHeight > list.height + 1
    anchors.right: list.right
    anchors.rightMargin: Style.spacing.xs
    width: Style.space(2)
    radius: width / 2
    color: Util.alpha(Commons.Color.menu.text, 0.18)
    height: Math.max(Style.space(24),
                     list.height * list.height / Math.max(1, list.contentHeight))
    y: (list.contentY / Math.max(1, list.contentHeight - list.height))
       * (list.height - height)
  }
}
