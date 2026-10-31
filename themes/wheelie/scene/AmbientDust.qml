pragma ComponentBehavior: Bound
import QtQuick

Item {
  id: root
  property real seconds
  // 2376 seconds is a whole number of every slot period. Keeping the clock small preserves
  // sub-frame precision during long sessions.
  property real clock: seconds % 2376
  property int epoch: Math.floor(seconds / 2376)
  property var rear: null // The rear wheel, which kicks up the spray; its radius sets the spray's size.
  property color sand: "transparent"
  property int seed: Math.floor(Math.random() * 8388591) + 1

  // Match ImageParticle's 8-bit premultiplied colors.
  function tint(r, g, b, a) {
    return Qt.vector4d(Math.round(r * a * 255) / 255, Math.round(g * a * 255) / 255,
                       Math.round(b * a * 255) / 255, Math.round(a * 255) / 255)
  }
  // Loose sand lifts briefly, spreads, and settles beside the painted ground trail, measured in
  // rear-wheel radii so it keeps its size at any resolution. Grains land: none falls through the sand.
  readonly property var spray: {
    if (!rear || !width) return []
    const r = rear.radius, x = rear.center[0], y = rear.contactY, w = width, h = height
    return [
      { rate: 32, life: 0.75, variation: 0.21, area: Qt.vector4d((x + 0.3 * r) / w, (y - 0.14 * r) / h, 0.2 * r / w, 0.04 * r / h),
        velocity: Qt.vector4d(1.56 * r, -0.9 * r, 0.55 * r, 0.4 * r), sizes: Qt.vector3d(0.025 * r, 0.012 * r, 0.01 * r),
        shape: Qt.vector4d(1, 1, 180, 0), tint: tint(sand.r, sand.g, sand.b, 0.4), wisp: true,
        force: Qt.vector4d(0, 3 * r, 0, y - 0.08 * r) },
      { rate: 22, life: 1.6, variation: 0.4, area: Qt.vector4d((x + 0.35 * r) / w, (y - 0.16 * r) / h, 0.4 * r / w, 0.06 * r / h),
        velocity: Qt.vector4d(1.5 * r, -0.64 * r, 0.6 * r, 0.14 * r), sizes: Qt.vector3d(0.28 * r, 0.9 * r, 0.12 * r),
        shape: Qt.vector4d(1.35, 0.6, 35, 25), tint: tint(sand.r, sand.g, sand.b, 0.32), wisp: true,
        force: Qt.vector4d(0, 0.4 * r, 1, 0) }
    ]
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
    ].concat(root.spray)
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
      property vector4d force: modelData.force || Qt.vector4d(0, 0, 0, 0)
      property var source: index === 2 || modelData.wisp ? wisp : grain
      // Two columns form each quad; one connector column collapses the triangles between slots.
      mesh: Qt.size(3 * count - 2, 1)
      vertexShader: Qt.resolvedUrl("ambient-dust.vert.qsb")
      fragmentShader: Qt.resolvedUrl("ambient-dust.frag.qsb")
    }
  }
}
