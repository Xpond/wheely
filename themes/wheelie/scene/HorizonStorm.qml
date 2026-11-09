import QtQuick

Item {
  id: root
  property real seconds
  property real horizon: 0 // Scene row where the storm ends, just inside the redrawn dunes.
  property real decode: 1 // The share of native resolution to decode, as in Surface.qml.

  ShaderEffect {
    width: parent.width; height: root.horizon
    property real extent: height / Math.max(1, root.height)
    // Approach once over four minutes, then keep rolling at the distant dunes.
    property real approach: Math.sin(Math.min(1, root.seconds / 240) * Math.PI / 2)
    // Circular noise coordinates keep the ten-minute billowing loop seamless.
    property real phase: (root.seconds % 600) / 600 * Math.PI * 2
    property real sceneAspect: root.width / Math.max(1, root.height)
    // storm.png keeps only the plate's top 1960 of 2688 rows, all the storm ever samples.
    property real kept: 1960 / 2688
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
