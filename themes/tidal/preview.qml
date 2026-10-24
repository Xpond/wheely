pragma ComponentBehavior: Bound
import QtQuick
import "animated"

Window {
  id: gallery
  width: 1440
  height: 1000
  visible: true
  color: "#ECECE8"
  title: "Tidal — wallpaper collection"
  property bool running: true

  Item {
    id: page
    width: 1440; height: 1000
    anchors.centerIn: parent
    scale: Math.min(gallery.width / width, gallery.height / height)
    Rectangle { anchors.fill: parent; color: "#ECECE8" }

    Text {
      x: 44; y: 24
      text: "AN OMARCHY THEME"
      color: "#506566"
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
      color: "#506566"
      font { family: "sans-serif"; pixelSize: 14 }
    }
    Row {
      x: page.width - width - 44; y: 43
      spacing: 10
      Repeater {
        model: ["#F2F2EE", "#D6E1DB", "#7FBDB4", "#146A7C", "#23444C"]
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
      text: gallery.running ? "SPACE  Pause the tide     ESC  Close" : "SPACE  Resume the tide     ESC  Close"
      color: "#506566"
      font { family: "sans-serif"; pixelSize: 12 }
    }

    Row {
      x: 44; y: 138; spacing: 18
      Repeater {
        model: [
          { muted: 0, label: "01  /  THE LIVING COAST" },
          { muted: 1, label: "02  /  THE MUTED COAST" }
        ]
        Item {
          id: coast
          required property var modelData
          width: (page.width - 106) / 2; height: 528
          clip: true
          Surface { anchors.fill: parent; muted: coast.modelData.muted; running: gallery.running }
          Rectangle {
            x: 20; y: 20; width: label.width + 32; height: 34
            color: "#E6F2F2EE"
            Text {
              id: label
              anchors.centerIn: parent
              text: coast.modelData.label
              color: "#23444C"
              font { family: "sans-serif"; pixelSize: 10; letterSpacing: 1.5 }
            }
          }
        }
      }
    }

    Row {
      x: 44; y: 690; spacing: 18
      Repeater {
        model: [
          { file: "01-shoreline", label: "03  /  SHORELINE", note: "The sea meets the sand." },
          { file: "02-shallows", label: "04  /  SHALLOWS", note: "Sunlight, held in water." },
          { file: "03-ebb", label: "05  /  EBB", note: "What the tide leaves behind." }
        ]
        Column {
          required property var modelData
          width: (page.width - 124) / 3
          spacing: 12
          Image {
            width: parent.width; height: 232
            source: Qt.resolvedUrl("backgrounds/" + parent.modelData.file + ".jpg")
            fillMode: Image.PreserveAspectCrop
            // Decoded near display size: full size is ~67 MB each.
            sourceSize.width: width * 2
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
            color: "#506566"
            font { family: "sans-serif"; pixelSize: 12 }
          }
        }
      }
    }
  }

  Shortcut { sequence: "Space"; onActivated: gallery.running = !gallery.running }
  Shortcut { sequence: "Escape"; onActivated: Qt.quit() }
}
