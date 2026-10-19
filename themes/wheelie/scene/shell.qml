import QtQuick
import Quickshell

FloatingWindow {
  title: "Wheelie 4K wallpaper preview"
  implicitWidth: 1376
  implicitHeight: 768
  color: "black"
  Surface {
    anchors.centerIn: parent
    // Preserve the generator's native aspect ratio.
    width: Math.min(parent.width, parent.height * 5504 / 3072)
    height: width * 3072 / 5504
  }
}
