import QtQuick

Item {
  id: root
  property bool running: true
  property real horizon: 0 // Scene row where the storm ends, just inside the redrawn dunes.
  property real approach: 0
  property real phase: 0

  // Approach once over four minutes, then keep rolling at the distant dunes.
  NumberAnimation on approach {
    from: 0; to: 1; duration: 240000
    easing.type: Easing.OutSine
    paused: !root.running
  }
  // Circular noise coordinates keep the ten-minute billowing loop seamless.
  NumberAnimation on phase {
    from: 0; to: Math.PI * 2; duration: 600000
    loops: Animation.Infinite; paused: !root.running
  }

  ShaderEffect {
    width: parent.width; height: root.horizon
    property real extent: height / Math.max(1, root.height)
    property real approach: root.approach
    property real phase: root.phase
    property real sceneAspect: root.width / Math.max(1, root.height)
    property real textureAspect: stormImage.implicitWidth / Math.max(1, stormImage.implicitHeight)
    property var storm: Image {
      id: stormImage
      source: "storm.png"
      cache: false
      visible: false
      smooth: true
    }
    fragmentShader: Qt.resolvedUrl("storm-wall.frag.qsb")
  }
}
