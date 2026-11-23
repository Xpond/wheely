import QtQuick

Item {
  id: root
  property real seconds
  property real horizon: 0 // Scene row where the storm ends, where the foreground sand begins.
  property real decode: 1 // The share of native resolution to decode, as in Surface.qml.
  property real light: 0 // 1 turns the storm a daylight haze.

  ShaderEffect {
    width: parent.width; height: root.horizon
    property real extent: height / Math.max(1, root.height)
    // Approach once over 24 seconds, then keep rolling at the distant dunes.
    property real approach: Math.sin(Math.min(1, root.seconds / 24) * Math.PI / 2)
    // Circular noise coordinates keep the one-minute billowing loop seamless.
    property real phase: (root.seconds % 60) / 60 * Math.PI * 2
    property real sceneAspect: root.width / Math.max(1, root.height)
    // storm.png keeps the plate's top 2380 of 2688 rows, all the storm ever samples.
    property real kept: 2380 / 2688
    property real light: root.light
    property real textureAspect: stormImage.implicitWidth / Math.max(1, stormImage.implicitHeight) * kept
    property var storm: Image {
      id: stormImage
      source: "storm.png"; cache: false
      visible: false
      smooth: true
      // Drawn up to 1.15 times the scene's width; 0 keeps the plate's native size.
      sourceSize.width: root.decode < 1 ? Math.ceil(root.width * root.decode * 1.15) : 0
    }
    fragmentShader: Qt.resolvedUrl("storm-wall.frag.qsb")
  }
}
