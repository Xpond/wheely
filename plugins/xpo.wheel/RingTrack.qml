import QtQuick
import qs.Commons
import qs.Commons as Commons

Item {
  id: root
  required property var wheel
  required property var discMask
  required property real spin

  ShaderEffect {
    anchors.fill: parent
    readonly property vector2d resolution: Qt.vector2d(width, height)
    readonly property real ringRadius: root.wheel.ringRadius
    readonly property real bandWidth: Style.space(2)
    readonly property real arcFrom: root.wheel.arcFrom * Math.PI / 180
    readonly property real arcSpan: root.wheel.arcSpan * Math.PI / 180
    readonly property real direction: root.wheel.arcDrag < 0 ? -1 : 1
    readonly property real motion: Math.min(1, Math.abs(root.wheel.arcDrag) / root.wheel.arcSpread)
    readonly property real spin: root.spin
    readonly property color baseColor: Commons.Color.menu.text
    readonly property color tint: root.wheel.cometColor
    readonly property var discMask: root.discMask
    property real presence: root.wheel.selected >= 0 || Math.abs(root.wheel.arcDrag) > 0.5 ? 1 : 0
    Behavior on presence { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
    fragmentShader: Qt.resolvedUrl("ring.frag.qsb")
  }
}
