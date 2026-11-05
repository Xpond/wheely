import QtQuick

// A settled coast with a quiet tide and slowly drifting water light.
ShaderEffect {
  id: root
  property bool running: true
  property real muted: 0
  property real seconds: 148
  readonly property vector2d resolution: Qt.vector2d(width, height)
  readonly property real time: seconds % 3600
  property double previous: Date.now()
  // A fractional output's true ratio comes from its window: Screen's is rounded up, 1.5 to 2.
  property real dpr: Screen.devicePixelRatio || 1
  blending: false
  // Wave geometry and old tide marks depend only on the horizontal position.
  property var surgeData: ShaderEffectSource {
    sourceItem: ShaderEffect {
      width: root.width
      height: 4
      readonly property vector2d resolution: root.resolution
      blending: false
      fragmentShader: Qt.resolvedUrl("geometry.frag.qsb")
    }
    textureSize: Qt.size(Math.ceil(root.width * root.dpr), 4)
    format: ShaderEffectSource.RGBA32F
    hideSource: true
    smooth: false
  }
  property var bubbles: ShaderEffectSource {
    sourceItem: Image { source: Qt.resolvedUrl("bubbles.png") }
    hideSource: true
    live: false
    smooth: true
    mipmap: true
    wrapMode: ShaderEffectSource.Repeat
  }
  // Four corner hashes per cell; keep full precision for the original noise and slopes.
  property var noiseData: ShaderEffectSource {
    sourceItem: ShaderEffect {
      width: 64
      height: 64
      blending: false
      fragmentShader: Qt.resolvedUrl("noise.frag.qsb")
    }
    textureSize: Qt.size(64, 64)
    format: ShaderEffectSource.RGBA32F
    hideSource: true
    smooth: false
    wrapMode: ShaderEffectSource.Repeat
  }

  onRunningChanged: previous = Date.now()
  Timer {
    interval: 32
    repeat: true
    running: root.running && root.visible
    onTriggered: {
      var now = Date.now()
      // A clock stepped backward must not run the sea backward.
      root.seconds += Math.max(0, Math.min(0.1, (now - root.previous) / 1000)) * 0.25
      root.previous = now
    }
  }

  fragmentShader: Qt.resolvedUrl("tidal.frag.qsb")
}
