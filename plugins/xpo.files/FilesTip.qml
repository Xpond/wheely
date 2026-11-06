import QtQuick
import qs.Commons
import qs.Commons as Commons

// A hovered name popped up whole over where it is drawn, wrapped past maxWidth. The list and a
// folder's preview each place one.
Rectangle {
  id: tip
  property alias text: label.text
  property alias pixelSize: label.font.pixelSize
  property real maxWidth: 0
  readonly property int pad: Style.spacing.sm
  width: label.width + pad * 2
  height: label.height + pad * 2
  radius: Style.space(8)
  color: Util.alpha(Commons.Color.menu.background, 0.98)
  border.width: Style.spacing.hairline
  border.color: Util.alpha(Commons.Color.menu.text, 0.13)

  Text {
    id: label
    x: tip.pad; y: tip.pad
    width: Math.min(implicitWidth, tip.maxWidth - tip.pad * 2)
    wrapMode: Text.WrapAnywhere
    color: Commons.Color.menu.text
    font.family: Style.font.menuFamily
  }
}
