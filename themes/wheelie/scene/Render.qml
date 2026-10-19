import QtQuick
import QtQuick.Window
import Quickshell

// Offscreen stills use the exact same layers and shaders as the live preview.
Window {
  width: Number(Quickshell.env("WHEELIE_WIDTH"))
  height: Number(Quickshell.env("WHEELIE_HEIGHT"))
  visible: true
  Loader {
    id: scene
    anchors.fill: parent
    source: "Surface.qml"
    onLoaded: {
      item.running = false
      item.particlesRunning = true // Populate the air while holding the requested wheel angle.
      item.wheelTurn = ((-Number(Quickshell.env("WHEELIE_ANGLE")) / 360) % 1 + 1) % 1
    }
  }
  Timer {
    interval: 1000; running: scene.status === Loader.Ready
    onTriggered: scene.item.grabToImage(function(result) {
      const saved = result.saveToFile(Quickshell.env("WHEELIE_OUTPUT"))
      Qt.exit(saved ? 0 : 1)
    })
  }
}
