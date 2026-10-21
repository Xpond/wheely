pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "MenuIndex.js" as MenuIndex

// The whole manual at once: one panel, a card per section, keys drawn as keycaps. Typing fades
// the rows search would not find. It is drawn from the parsed rows, so nothing here can edit
// the file. Its columns take the width they are given, and what runs past the height scrolls.
Item {
  id: sheet
  property var wheel: null
  property alias filterSlot: filter

  readonly property var rows: sheet.wheel.manualRows.filter(function (r) { return !!r.section })
  readonly property string term: sheet.wheel.query.trim()
  // Rows by what they say: a model hands each delegate its own copy, so identity is no test.
  function idOf(row) { return row.section + "\n" + row.keys + "\n" + row.label }
  readonly property var found: sheet.term ? MenuIndex.search(sheet.rows, sheet.term, sheet.rows.length, {}).map(sheet.idOf) : []
  function lit(row) { return !sheet.term || sheet.found.indexOf(sheet.idOf(row)) >= 0 }

  readonly property int gap: Style.space(24)
  readonly property int pad: Style.spacing.panelPadding
  // Read at arm's length, so larger than the shell's own text.
  readonly property int textSize: Style.fontPx(1.25)
  readonly property int keySize: Style.font.subtitle
  readonly property int capHeight: sheet.keySize + Style.spacing.xs * 3
  // On the overlay the panel keeps clear of the screen's edges; a window is its own frame.
  readonly property real room: sheet.width * (sheet.wheel.windowed ? 1 : 0.88)
  // Up to three columns, as wide as the room allows: outer margins, the panel's padding, and gaps.
  readonly property int count: Math.max(1, Math.min(3, Math.floor((sheet.room - sheet.gap) / (Style.space(400) + sheet.gap))))
  readonly property int columnWidth: Math.min(Style.space(560), Math.floor((sheet.room - sheet.gap * (sheet.count + 3)) / sheet.count))
  readonly property int keyWidth: Math.round(sheet.columnWidth * 0.42)
  readonly property var columns: MenuIndex.manualColumns(sheet.rows, sheet.count)

  // Lines down, or up when negative.
  function scroll(lines) {
    var bottom = Math.max(0, scroller.contentHeight - scroller.height)
    scroller.contentY = Math.max(0, Math.min(bottom, scroller.contentY + lines * sheet.capHeight * 1.5))
  }

  anchors.fill: parent
  opacity: sheet.wheel.reading ? 1 : 0
  visible: opacity > 0
  Behavior on opacity { NumberAnimation { duration: sheet.wheel.fadeDuration; easing.type: Easing.OutCubic } }
  onVisibleChanged: scroller.contentY = 0

  Flickable {
    id: scroller
    anchors.fill: parent
    contentHeight: Math.max(height, panel.height + panel.y * 2)
    interactive: contentHeight > height
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    BorderSurface {
      id: panel
      x: (scroller.width - width) / 2
      y: Math.max(sheet.gap, (scroller.height - height) / 2)
      width: content.width + sheet.gap * 2
      height: content.height + sheet.gap * 2
      radius: Style.space(24)
      color: sheet.wheel.surfaceFill
      borderSpec: Border.flat(sheet.wheel.surfaceEdge, Style.spacing.hairline)

      ClickShield {}

      Column {
        id: content
        x: sheet.gap
        y: sheet.gap
        spacing: sheet.gap

        Item {
          width: columnsRow.width
          height: filter.height

          Text {
            id: title
            anchors.verticalCenter: parent.verticalCenter
            text: "Wheely manual"
            color: Commons.Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.fontPx(1.333)
            font.bold: true
          }
          // The wheel's query field moves here while the manual is open.
          BorderSurface {
            id: filter
            anchors.centerIn: parent
            // Centered, and clear of the title and the hint on either side.
            width: Math.min(sheet.wheel.searchWidth, parent.width - (Math.max(title.width, hint.width) + sheet.gap) * 2)
            height: sheet.wheel.searchHeight
            radius: height / 2
            color: sheet.wheel.surfaceFill
            borderSpec: Border.flat(sheet.term ? Commons.Color.accent : sheet.wheel.surfaceEdge, Style.spacing.hairline)
            Text {
              anchors.centerIn: parent
              text: "type to filter"
              visible: !sheet.term
              opacity: 0.45
              color: Commons.Color.menu.text
              font.family: Style.font.menuFamily
              font.pixelSize: Style.font.subtitle
            }
          }
          Text {
            id: hint
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: parent.right
            text: (sheet.wheel.windowed ? "" : "ctrl+t pin  ·  ") + "esc back"
            opacity: 0.5
            color: Commons.Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
        }

        Row {
          id: columnsRow
          spacing: sheet.gap

          Repeater {
            model: sheet.columns
            Column {
              required property var modelData
              width: sheet.columnWidth
              spacing: sheet.gap

              Repeater {
                model: parent.modelData
                BorderSurface {
                  id: section
                  required property var modelData
                  width: sheet.columnWidth
                  height: body.height + sheet.pad * 2
                  radius: Style.space(18)
                  color: Util.alpha(Commons.Color.menu.text, 0.03)
                  borderSpec: Border.flat(sheet.wheel.surfaceEdge, Style.spacing.hairline)

                  Column {
                    id: body
                    x: sheet.pad
                    y: sheet.pad
                    width: parent.width - sheet.pad * 2

                    Text {
                      bottomPadding: Style.spacing.sm
                      text: section.modelData.name.toUpperCase()
                      opacity: section.modelData.rows.some(sheet.lit) ? 0.6 : 0.2
                      color: Commons.Color.menu.text
                      font.family: Style.font.menuFamily
                      font.pixelSize: Style.font.body
                      font.letterSpacing: 1.5
                    }

                    Repeater {
                      model: section.modelData.rows
                      // A rule above every row but the first parts one key from the next.
                      Item {
                        id: entry
                        required property var modelData
                        required property int index
                        readonly property bool lit: sheet.lit(modelData)
                        width: body.width
                        height: Math.max(keys.height, label.y - keys.y + label.height) + Style.spacing.sm * 2

                        Rectangle {
                          visible: entry.index > 0
                          width: parent.width
                          height: Style.spacing.hairline
                          color: sheet.wheel.surfaceEdge
                        }

                        Item {
                          anchors.fill: parent
                          opacity: entry.lit ? 1 : 0.25
                          Behavior on opacity { NumberAnimation { duration: 120 } }

                          // Lines break between combos, never inside one.
                          Flow {
                            id: keys
                            y: Style.spacing.sm
                            width: sheet.keyWidth
                            spacing: Style.spacing.sm
                            Repeater {
                              model: MenuIndex.combosOf(entry.modelData)
                              Row {
                                id: combo
                                required property var modelData
                                height: sheet.capHeight
                                spacing: Style.spacing.xs
                                Text {
                                  visible: !!combo.modelData.plain
                                  anchors.verticalCenter: parent.verticalCenter
                                  text: combo.modelData.plain
                                  color: Commons.Color.menu.text
                                  font.family: Style.font.menuFamily
                                  font.pixelSize: sheet.keySize
                                }
                                Repeater {
                                  model: combo.modelData.caps
                                  BorderSurface {
                                    required property string modelData
                                    width: Math.max(sheet.capHeight, cap.implicitWidth + Style.spacing.sm * 2)
                                    height: sheet.capHeight
                                    radius: Style.spacing.xs * 2
                                    color: Util.alpha(Commons.Color.menu.text, 0.06)
                                    borderSpec: Border.flat(sheet.wheel.surfaceEdge, Style.spacing.hairline)
                                    Text {
                                      id: cap
                                      anchors.centerIn: parent
                                      text: parent.modelData
                                      color: Commons.Color.menu.text
                                      font.family: Style.font.menuFamily
                                      font.pixelSize: sheet.keySize
                                    }
                                  }
                                }
                              }
                            }
                          }
                          // Its first line level with the first row of keys.
                          Text {
                            id: label
                            x: sheet.keyWidth + Style.spacing.md
                            y: keys.y + Math.max(0, (sheet.capHeight - contentHeight / Math.max(1, lineCount)) / 2)
                            width: parent.width - x
                            text: entry.modelData.label
                            wrapMode: Text.Wrap
                            color: Commons.Color.menu.text
                            font.family: Style.font.menuFamily
                            font.pixelSize: sheet.textSize
                          }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
