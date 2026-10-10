import QtQuick
import Quickshell
import "animated"

Window {
  id: gallery
  width: 1440
  height: 1000
  visible: true
  color: "#F4F1E8"
  title: "Tidal — wallpaper collection"

  Item {
    id: page
    width: 1440; height: 1000
    anchors.centerIn: parent
    scale: Math.min(gallery.width / width, gallery.height / height)
    Rectangle { anchors.fill: parent; color: "#F4F1E8" }

    Text {
      x: 44; y: 24
      text: "AN OMARCHY THEME"
      color: "#5C7273"
      font { family: "sans-serif"; pixelSize: 10; letterSpacing: 2.5 }
    }
    Text {
      x: 42; y: 42
      text: "Tidal"
      color: "#23444C"
      font { family: "sans-serif"; pixelSize: 42; weight: Font.DemiBold; letterSpacing: -1.5 }
    }
    Text {
      x: 44; y: 99
      text: "Chalk, sea glass, and a little motion."
      color: "#5C7273"
      font { family: "sans-serif"; pixelSize: 14 }
    }
    Row {
      x: page.width - width - 44; y: 43
      spacing: 10
      Repeater {
        model: ["#F8F7F0", "#D6E1DB", "#7FBDB4", "#146A7C", "#23444C"]
        Rectangle {
          required property string modelData
          width: 32; height: 32; radius: 16
          color: modelData
          border { width: 1; color: "#BBCDC8" }
        }
      }
    }
    Text {
      x: page.width - width - 44; y: 99
      text: sea.running ? "SPACE  Pause the tide     ESC  Close" : "SPACE  Resume the tide     ESC  Close"
      color: "#5C7273"
      font { family: "sans-serif"; pixelSize: 12 }
    }

    Item {
      x: 44; y: 138; width: page.width - 88; height: 528
      clip: true
      Surface { id: sea; anchors.fill: parent }
      Rectangle {
        x: 20; y: 20; width: label.width + 32; height: 34
        color: "#E6F8F7F0"
        Text {
          id: label
          anchors.centerIn: parent
          text: "01  /  THE LIVING COAST"
          color: "#23444C"
          font { family: "sans-serif"; pixelSize: 10; letterSpacing: 1.5 }
        }
      }
    }

    Row {
      x: 44; y: 690; spacing: 18
      Repeater {
        model: [
          { file: "01-shoreline", label: "02  /  SHORELINE", note: "The sea meets the sand." },
          { file: "02-shallows", label: "03  /  SHALLOWS", note: "Sunlight, held in water." },
          { file: "03-ebb", label: "04  /  EBB", note: "What the tide leaves behind." }
        ]
        Column {
          required property var modelData
          width: (page.width - 124) / 3
          spacing: 12
          Image {
            width: parent.width; height: 232
            source: Qt.resolvedUrl("backgrounds/" + parent.modelData.file + ".jpg")
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            smooth: true
          }
          Text {
            text: parent.modelData.label
            color: "#23444C"
            font { family: "sans-serif"; pixelSize: 10; letterSpacing: 1.5 }
          }
          Text {
            text: parent.modelData.note
            color: "#5C7273"
            font { family: "sans-serif"; pixelSize: 12 }
          }
        }
      }
    }
  }

  Shortcut { sequence: "Space"; onActivated: sea.running = !sea.running }
  Shortcut { sequence: "Escape"; onActivated: Qt.quit() }
}
