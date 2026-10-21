pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// Ranked search results using the ring's visual language.
Item {
  id: stack
  property var wheel: null

  anchors.top: parent.verticalCenter
  anchors.topMargin: stack.wheel.searchHeight / 2 + Style.spacing.panelGap
  anchors.horizontalCenter: parent.horizontalCenter
  // Disable hit testing after the transition back to the ring.
  transformOrigin: Item.Top
  opacity: stack.wheel.searching && !stack.wheel.reading ? 1 : 0
  scale: stack.wheel.searching && !stack.wheel.reading ? 1 : 0.96
  visible: opacity > 0
  Behavior on opacity { NumberAnimation { duration: stack.wheel.fadeDuration; easing.type: Easing.OutCubic } }
  Behavior on scale { NumberAnimation { duration: stack.wheel.fadeDuration; easing.type: Easing.OutCubic } }
  width: stack.wheel.searchWidth
  height: resultList.height
  layer.enabled: true
  layer.effect: MultiEffect {
    shadowEnabled: true
    blurMax: 16
    shadowOpacity: 0.4
    shadowVerticalOffset: Style.space(3)
  }

  ClickShield {}

  // Track the cursor even before rows appear; their hover events can be synthetic.
  HoverHandler {
    parent: stack.Window.window ? stack.Window.window.contentItem : stack
    onPointChanged: {
      if (!stack.wheel.hoverMoved(point.scenePosition) || !stack.visible) return
      var pt = resultList.mapFromItem(parent, point.position.x, point.position.y)
      var row = resultList.childAt(pt.x, pt.y) as ResultCard
      if (row) stack.wheel.resultIndex = row.row
    }
  }

  Column {
    id: resultList
    anchors.horizontalCenter: parent.horizontalCenter
    width: stack.wheel.resultWidth
    spacing: Style.spacing.md

    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      visible: stack.wheel.results.length === 0
      horizontalAlignment: Text.AlignHCenter
      text: stack.wheel.emptyText
      color: Commons.Color.menu.text
      opacity: 0.5
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.body
    }

    Repeater {
      model: stack.wheel.beads
      component ResultCard: BorderSurface {
        id: resultCard
        required property int index
        required property var modelData
        readonly property int row: stack.wheel.resultTop + index
        readonly property bool active: stack.wheel.resultIndex === resultCard.row
        // A setting row being changed says what saving would do; the field shows what was pressed.
        readonly property bool editing: !!resultCard.modelData.setting && resultCard.modelData.setting === stack.wheel.editing

        width: stack.wheel.resultWidth
        height: stack.wheel.resultHeight
        radius: height / 2
        color: active ? stack.wheel.selectedFill : stack.wheel.surfaceFill
        borderSpec: Border.flat(active ? stack.wheel.cometColor : stack.wheel.surfaceEdge,
                                Style.spacing.hairline)

        Behavior on color { ColorAnimation { duration: 90 } }

        // A MouseArea's own wheel signal shadows the property here, so the wheel goes by the stack.
        MouseArea {
          anchors.fill: parent
          onClicked: stack.wheel.run(stack.wheel.results[resultCard.row])
        }

        Row {
          id: resultRow
          anchors.verticalCenter: parent.verticalCenter
          anchors.left: parent.left
          anchors.leftMargin: Style.spacing.rowPaddingX
          anchors.right: parent.right
          anchors.rightMargin: Style.spacing.rowPaddingX
          spacing: Style.spacing.controlGap

          readonly property real textBudget:
            Math.max(0, width - Style.font.iconLarge - spacing * 2 - chevron.width
                        - (valueField.visible ? valueField.width + spacing : 0)
                        - (valueSlider.visible ? valueSlider.width + spacing : 0))

          Text {
            anchors.verticalCenter: parent.verticalCenter
            visible: (!resultCard.modelData.appIcon || appImage.status === Image.Error) && !resultCard.modelData.iconFile
            width: Style.font.iconLarge
            text: resultCard.modelData.icon
            color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
            font.family: resultCard.modelData.iconFont || Style.font.menuFamily
            font.pixelSize: Style.font.iconLarge
          }
          PanelIcon {
            omarchyPath: stack.wheel.omarchyPath
            anchors.verticalCenter: parent.verticalCenter
            width: Style.font.iconLarge
            file: resultCard.modelData.iconFile || ""
            size: Style.font.iconLarge
            tint: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
          }
          // Fall back to the glyph when a themed icon fails to load.
          Image {
            id: appImage
            anchors.verticalCenter: parent.verticalCenter
            visible: !!resultCard.modelData.appIcon && status !== Image.Error
            width: Style.font.iconLarge
            height: Style.font.iconLarge
            source: resultCard.modelData.appIcon ? stack.wheel.appLibrary.iconSource(resultCard.modelData.appIcon) : ""
            sourceSize.width: Style.font.iconLarge
            sourceSize.height: Style.font.iconLarge
            fillMode: Image.PreserveAspectFit
            asynchronous: true
          }
          Text {
            id: labelText
            anchors.verticalCenter: parent.verticalCenter
            visible: !resultCard.modelData.copy
            width: Math.min(implicitWidth, resultRow.textBudget - trailText.width)
            elide: Text.ElideRight
            text: resultCard.editing ? stack.wheel.editNote : resultCard.modelData.label
            color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
          Text {
            id: trailText
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth,
                            Math.max(resultRow.textBudget * 0.4,
                                     resultRow.textBudget - labelText.implicitWidth))
            text: resultCard.modelData.setting ? "" : resultCard.modelData.trail
            color: Commons.Color.menu.text
            opacity: 0.45
            // Preserve the filename end of paths and the root of breadcrumbs.
            elide: resultCard.modelData.path ? Text.ElideLeft : Text.ElideRight
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.caption
          }
          Text {
            id: chevron
            anchors.verticalCenter: parent.verticalCenter
            width: resultCard.modelData.node ? implicitWidth + parent.spacing : 0
            visible: !!resultCard.modelData.node
            text: "\u203a"
            color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
            opacity: 0.5
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.body
          }
        }

        // A setting row ends in its value, drawn as a control, the way Omarchy's panel rows end in one.
        BorderSurface {
          id: valueField
          anchors.verticalCenter: parent.verticalCenter
          anchors.right: resultRow.right
          visible: !!resultCard.modelData.setting && !valueSlider.visible && !resultCard.editing
          width: valueText.implicitWidth + Style.spacing.controlPaddingX * 2
          height: valueText.implicitHeight + Style.spacing.xs * 2
          radius: height / 2
          color: Style.controlFill(resultCard.active, false, Commons.Color.menu.text, Commons.Color.accent)
          borderSpec: Border.controlSpec(resultCard.active ? "focus" : "normal", Commons.Color.menu.text, Commons.Color.accent)

          Text {
            id: valueText
            anchors.centerIn: parent
            text: resultCard.modelData.trail
            color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.caption
          }
        }

        // The backdrop's is Omarchy's slider, moved by ←/→ only, so the pointer passes to the row.
        PanelSlider {
          id: valueSlider
          anchors.verticalCenter: parent.verticalCenter
          anchors.right: resultRow.right
          visible: resultCard.modelData.setting === "backdrop"
          enabled: false
          width: Style.space(72)
          bar: QtObject {
            readonly property color foreground: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
            readonly property color background: Commons.Color.menu.background
          }
          maximum: 100
          value: stack.wheel.backdrop
        }

        // An answer centers under its query and, like the query, overflows to the left.
        Text {
          anchors.centerIn: parent
          visible: !!resultCard.modelData.copy
          width: Math.min(implicitWidth, resultRow.width - 2 * (Style.font.iconLarge + resultRow.spacing))
          elide: Text.ElideLeft
          text: resultCard.modelData.label
          color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }
        Text {
          anchors.verticalCenter: parent.verticalCenter
          anchors.right: resultRow.right
          visible: !!resultCard.modelData.copy
          text: "󰆏"
          color: resultCard.active ? Commons.Color.accent : Commons.Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.iconLarge
        }
      }
      delegate: ResultCard {}
    }
  }

  Rectangle {
    readonly property int span: Math.max(1, stack.wheel.results.length - stack.wheel.resultCap)
    visible: stack.wheel.results.length > stack.wheel.resultCap
    anchors.right: parent.right
    width: Style.space(2)
    radius: width / 2
    color: Util.alpha(Commons.Color.menu.text, 0.18)
    height: resultList.height * stack.wheel.resultCap / stack.wheel.results.length
    y: stack.wheel.resultTop / span * (resultList.height - height)
  }
}
