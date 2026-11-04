pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// Used twice: the main menu and its single submenu. Both cards stay mounted.
BorderSurface {
  id: card
  required property var menu
  required property var rows
  property bool isSub: false
  property point at: Qt.point(0, 0)
  property real parentLeft: 0
  readonly property int margin: Style.spacing.sm

  TextMetrics {
    id: metrics
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.body
    text: "0"
  }
  width: Math.min(menu.width - margin * 2, Math.round(metrics.advanceWidth * 36) + Style.spacing.rowPaddingX * 2)
  height: Math.min(menu.height - margin * 2, column.height + margin * 2)
  // Submenus overlap the parent's edge slightly and flip left when the right side has no room.
  x: !isSub ? Math.max(margin, Math.min(at.x, menu.width - width - margin))
     : at.x - margin + width <= menu.width - margin ? at.x - margin : Math.max(margin, parentLeft - width + margin)
  y: Math.max(margin, Math.min(at.y - (isSub ? margin : 0), menu.height - height - margin))
  radius: Style.space(16)
  color: Util.alpha(Commons.Color.menu.background, 0.98)
  borderSpec: Border.flat(card.menu.panel.edge, Style.spacing.hairline)

  // The column places its rows when the frame is drawn, and a key can come first.
  function rowItem(id) {
    column.forceLayout()
    return lines.itemAt(card.rows.findIndex(r => r.id === id))
  }
  // Where the submenu of row id opens: past this menu's right edge, level with the row.
  function beside(id) {
    var row = card.rowItem(id)
    return Qt.point(card.x + card.width, row ? row.mapToItem(card.menu, 0, 0).y : card.y)
  }
  function resetScroll() { view.contentY = 0 }
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
    onPositionChanged: if (card.isSub) card.menu.hover(null, true)
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
        // A count preserves delegates when a probe replaces the row data.
        model: card.rows.length

        delegate: Item {
          id: line
          required property int index
          readonly property var modelData: card.rows[line.index] || ({})
          // The main menu keeps its open submenu highlighted.
          readonly property bool lit: !card.isSub && card.menu.submenu ? card.menu.submenu === line.modelData.id
                                                                     : card.menu.current === line.modelData.id
          readonly property bool armedRow: line.modelData.id === "trash" && card.menu.armed

          width: column.width
          height: line.modelData.sep ? Style.spacing.lg : Style.spacing.popupRowHeight

          Rectangle {
            visible: !!line.modelData.sep
            anchors.centerIn: parent
            width: parent.width - Style.spacing.md * 2
            height: Style.spacing.hairline
            color: card.menu.panel.edge
          }

          // The list's selection capsule; Trash fills red once armed, as its row in the list does.
          Rectangle {
            visible: !line.modelData.sep
            anchors.fill: parent
            radius: height / 2
            color: line.armedRow ? Util.alpha(card.menu.panel.danger, 0.30) : line.lit ? card.menu.panel.activeFill
                   : pointer.containsMouse ? card.menu.panel.hoverFill : "transparent"
            border.width: line.lit || line.armedRow ? Style.spacing.hairline : 0
            border.color: line.armedRow ? card.menu.panel.danger : Commons.Color.accent
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
            color: line.modelData.danger ? card.menu.panel.danger
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
            onPositionChanged: mouse => { if (card.menu.pointerGate.moved(pointer, mouse)) card.menu.hover(line.modelData, card.isSub) }
            onClicked: card.menu.fire(line.modelData, false, true)
          }
        }
      }
    }
  }
}
