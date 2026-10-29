pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// The dial, including its discs, labels, track, and comet.
Item {
  id: root

  property var wheel: null
  // Repeated passes merge into quiet illumination as sustained spin builds.
  property real spin: root.wheel.spinning ? 1 : 0
  Behavior on spin { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }

  anchors.fill: parent
  // Stop compositing after the transition to search results.
  opacity: root.wheel.searching ? 0 : 1
  scale: root.wheel.searching ? 0.94 : 1
  visible: opacity > 0
  Behavior on opacity { NumberAnimation { duration: root.wheel.fadeDuration; easing.type: Easing.OutCubic } }
  Behavior on scale { NumberAnimation { duration: root.wheel.fadeDuration; easing.type: Easing.OutCubic } }

  Item { id: discCutouts; anchors.fill: parent }
  ShaderEffectSource {
    id: maskTexture
    sourceItem: discCutouts
    hideSource: true
  }

  RingTrack {
    anchors.fill: parent
    wheel: root.wheel
    discMask: maskTexture
    spin: root.spin
  }

  Repeater {
    model: root.wheel.slices
    delegate: Item {
      id: slice
      required property int index
      required property var modelData
      readonly property bool active: root.wheel.selected === index
      property real emphasis: active ? 1 - root.spin * 0.9 : 0
      Behavior on emphasis { NumberAnimation { duration: 110; easing.type: Easing.OutCubic } }
      readonly property real targetLight: root.wheel.sweepAt(root.wheel.sliceAngle(index) - 90)
      property real light: targetLight
      Behavior on light {
        NumberAnimation { duration: slice.targetLight > slice.light ? 70 : 260; easing.type: Easing.OutCubic }
      }
      readonly property real sweep: root.spin * 0.24 + light * (1 - root.spin * 0.85)
      readonly property color glyphColor: Qt.tint(Commons.Color.menu.text,
        Util.alpha(root.wheel.cometColor, Math.max(slice.emphasis, slice.sweep)))
      readonly property real glyphSize: Style.font.displayLarge * root.wheel.itemSize / root.wheel.baseItem

      readonly property real angle: (root.wheel.sliceAngle(index) - 90) * Math.PI / 180
      x: root.width / 2 + root.wheel.ringRadius * Math.cos(angle) - width / 2
      y: root.height / 2 + root.wheel.ringRadius * Math.sin(angle) - height / 2
      width: root.wheel.itemSize
      height: root.wheel.itemSize

      // Cut the track beneath the animated disc, independent of its translucent fill.
      Rectangle {
        parent: discCutouts
        x: slice.x + (slice.width - width) / 2
        y: slice.y + (slice.height - height) / 2
        width: slice.width * disc.scale
        height: width
        radius: width / 2
        color: "black"
      }

      BorderSurface {
        id: disc
        anchors.fill: parent
        radius: width / 2
        color: Qt.rgba(
          root.wheel.surfaceFill.r + (root.wheel.selectedFill.r - root.wheel.surfaceFill.r) * slice.emphasis,
          root.wheel.surfaceFill.g + (root.wheel.selectedFill.g - root.wheel.surfaceFill.g) * slice.emphasis,
          root.wheel.surfaceFill.b + (root.wheel.selectedFill.b - root.wheel.surfaceFill.b) * slice.emphasis,
          root.wheel.surfaceFill.a + (root.wheel.selectedFill.a - root.wheel.surfaceFill.a) * slice.emphasis)
        borderSpec: Border.flat(Qt.tint(root.wheel.surfaceEdge,
          Util.alpha(root.wheel.cometColor, Math.max(slice.emphasis, slice.sweep * 0.9))),
          Style.spacing.hairline + (Style.space(2) - Style.spacing.hairline) * slice.emphasis)
        scale: 1 + (root.wheel.selectedScale - 1) * slice.emphasis

        Text {
          anchors.centerIn: parent
          visible: (!slice.modelData.appIcon || appImage.status === Image.Error) && !slice.modelData.iconFile
          text: slice.modelData.icon
          color: slice.glyphColor
          font.family: slice.modelData.iconFont || Style.font.menuFamily
          font.pixelSize: slice.glyphSize
        }
        // A pinned app wears its own icon, as its search row does.
        Image {
          id: appImage
          anchors.centerIn: parent
          visible: !!slice.modelData.appIcon && status !== Image.Error
          width: slice.glyphSize
          height: slice.glyphSize
          source: slice.modelData.appIcon ? root.wheel.appLibrary.iconSource(slice.modelData.appIcon) : ""
          sourceSize.width: slice.glyphSize
          sourceSize.height: slice.glyphSize
          fillMode: Image.PreserveAspectFit
          asynchronous: true
        }
        PanelIcon {
          omarchyPath: root.wheel.omarchyPath
          anchors.centerIn: parent
          file: slice.modelData.iconFile || ""
          size: slice.glyphSize
          tint: slice.glyphColor
        }
      }

      // Place labels radially outside each disc to clear the track and neighbors.
      Text {
        // Measure clearance to the label's nearest edge.
        readonly property real reach: root.wheel.itemSize / 2 * root.wheel.selectedScale + root.wheel.labelGap
          + (Math.abs(Math.cos(parent.angle)) * width
             + Math.abs(Math.sin(parent.angle)) * height) / 2
        x: parent.width / 2 + reach * Math.cos(parent.angle) - width / 2
        y: parent.height / 2 + reach * Math.sin(parent.angle) - height / 2
        text: slice.modelData.label
        color: Qt.tint(Commons.Color.menu.text, Util.alpha(Commons.Color.accent, slice.emphasis))
        opacity: 0.6 + 0.4 * slice.emphasis
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.caption
      }
    }
  }
}
