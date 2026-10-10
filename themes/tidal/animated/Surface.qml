import QtQuick

// The same coast on every display, with a still camera and a slow, hourly repeating tide.
ShaderEffect {
  id: root
  property bool running: true
  property real seconds: 148
  readonly property vector2d resolution: Qt.vector2d(width, height)
  readonly property real time: seconds % 3600
  property double previous: Date.now()

  onRunningChanged: previous = Date.now()
  Timer {
    interval: 32
    repeat: true
    running: root.running && root.visible
    onTriggered: {
      var now = Date.now()
      root.seconds += Math.min(0.1, (now - root.previous) / 1000) * 0.30
      root.previous = now
    }
  }

  fragmentShader: Qt.resolvedUrl("tidal.frag.qsb")
}
