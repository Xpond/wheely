pragma ComponentBehavior: Bound
import QtQuick

Item {
  id: root
  property bool running: true
  property real clock
  property int epoch: 0
  property int seed: Math.floor(Math.random() * 8388591) + 1

  // 2376 seconds is a whole number of 33-, 24- and 27-second slot periods.
  // Keeping the clock small preserves sub-frame precision during long sessions.
  SequentialAnimation on clock {
    loops: Animation.Infinite; paused: !root.running
    NumberAnimation { from: 0; to: 2376; duration: 2376000 }
    ScriptAction { script: root.epoch++ }
  }

  // Match ImageParticle's 8-bit premultiplied colors.
  function tint(r, g, b, a) {
    return Qt.vector4d(Math.round(r * a * 255) / 255, Math.round(g * a * 255) / 255,
                       Math.round(b * a * 255) / 255, Math.round(a * 255) / 255)
  }
  Image { id: grain; source: "sand-grain.svg"; visible: false }
  Image { id: wisp; source: "dust.svg"; visible: false }

  Repeater {
    model: [
      { rate: 224, life: 26, variation: 7, area: Qt.vector4d(-0.15, 0.10, 1.15, 0.66),
        velocity: Qt.vector4d(24, -5, 18, 10), sizes: Qt.vector3d(4, 4, 2),
        shape: Qt.vector4d(1, 1, 180, 22), tint: root.tint(0.72, 0.57, 0.39, 0.48) },
      { rate: 156, life: 18, variation: 6, area: Qt.vector4d(-0.20, 0.42, 1.20, 0.58),
        velocity: Qt.vector4d(85, -15, 40, 22), sizes: Qt.vector3d(12, 12, 7),
        shape: Qt.vector4d(0.7, 0.7, 180, 16), tint: root.tint(0.86, 0.76, 0.60, 0.48) },
      { rate: 1, life: 22, variation: 5, area: Qt.vector4d(-0.25, 0.68, 1.25, 0.27),
        velocity: Qt.vector4d(65, -8, 25, 8), sizes: Qt.vector3d(440, 700, 160),
        shape: Qt.vector4d(2.8, 0.3, 8, 0), tint: root.tint(0.72, 0.67, 0.58, 0.10) },
      { rate: 112, life: 26, variation: 7, area: Qt.vector4d(-0.15, 0.10, 1.15, 0.66),
        velocity: Qt.vector4d(24, -5, 18, 10), sizes: Qt.vector3d(4, 4, 2),
        shape: Qt.vector4d(1, 1, 180, 0), tint: Qt.vector4d(1, 1, 1, 1) },
      { rate: 78, life: 18, variation: 6, area: Qt.vector4d(-0.20, 0.42, 1.20, 0.58),
        velocity: Qt.vector4d(85, -15, 40, 22), sizes: Qt.vector3d(12, 12, 7),
        shape: Qt.vector4d(1, 1, 180, 0), tint: Qt.vector4d(1, 1, 1, 1) }
    ]
    ShaderEffect {
      required property var modelData
      required property int index
      width: root.width; height: root.height
      property real clock: root.clock
      property real epochOffset: (root.epoch * 2376 * rate) % 8388592
      property real seed: (root.seed + index * 1234567) % 8388592 + 1
      property vector2d extent: Qt.vector2d(width, height)
      property real period: modelData.life + modelData.variation
      property real rate: modelData.rate
      property real lifetime: modelData.life
      property real variation: modelData.variation
      property int count: Math.ceil(period * rate)
      property vector4d area: modelData.area
      property vector4d velocity: modelData.velocity
      property vector3d sizes: modelData.sizes
      property vector4d shape: modelData.shape
      property vector4d tint: modelData.tint
      property var source: index === 2 ? wisp : grain
      // One quad per slot; collapsed rows connect quads without drawing between them.
      mesh: Qt.size(1, 4 * count - 3)
      vertexShader: Qt.resolvedUrl("ambient-dust.vert.qsb")
      fragmentShader: Qt.resolvedUrl("ambient-dust.frag.qsb")
    }
  }
}
