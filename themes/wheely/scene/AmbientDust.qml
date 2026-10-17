import QtQuick
import QtQuick.Particles

// Native scene coordinates. Small distant grains drift more slowly than nearby sand.
Item {
  id: root
  property bool running: true

  // ImageParticle expects premultiplied color, like the rear-wheel dust.
  function tint(r, g, b, a) { return Qt.rgba(r * a, g * a, b * a, a) }

  ParticleSystem { id: air; paused: !root.running }
  ImageParticle {
    system: air; groups: ["distant"]
    source: "sand-grain.svg"
    color: root.tint(0.72, 0.57, 0.39, 0.48)
    rotationVariation: 180
    rotationVelocityVariation: 22
  }
  ImageParticle {
    system: air; groups: ["near"]
    source: "sand-grain.svg"
    color: root.tint(0.86, 0.76, 0.60, 0.48)
    rotationVariation: 180
    rotationVelocityVariation: 16
    xVector: PointDirection { x: 0.7; y: 0 }
    yVector: PointDirection { x: 0; y: 0.7 }
  }
  ImageParticle {
    system: air; groups: ["wisp"]
    source: "dust.svg"
    color: root.tint(0.72, 0.67, 0.58, 0.10)
    rotationVariation: 8
    xVector: PointDirection { x: 2.8; y: 0 }
    yVector: PointDirection { x: 0; y: 0.3 }
  }

  // Pre-roll fills the air immediately; emission also extends beyond the left edge.
  Emitter {
    system: air; group: "distant"
    x: -0.15 * root.width; y: 0.10 * root.height
    width: 1.15 * root.width; height: 0.66 * root.height
    emitRate: 224; lifeSpan: 26000; lifeSpanVariation: 7000; startTime: 33000
    size: 4; sizeVariation: 2
    velocity: PointDirection { x: 24; xVariation: 18; y: -5; yVariation: 10 }
  }
  Emitter {
    system: air; group: "near"
    x: -0.2 * root.width; y: 0.42 * root.height
    width: 1.2 * root.width; height: 0.58 * root.height
    emitRate: 156; lifeSpan: 18000; lifeSpanVariation: 6000; startTime: 24000
    size: 12; sizeVariation: 7
    velocity: PointDirection { x: 85; xVariation: 40; y: -15; yVariation: 22 }
  }
  Emitter {
    system: air; group: "wisp"
    x: -0.25 * root.width; y: 0.68 * root.height
    width: 1.25 * root.width; height: 0.27 * root.height
    emitRate: 1; lifeSpan: 22000; lifeSpanVariation: 5000; startTime: 27000
    size: 440; endSize: 700; sizeVariation: 160
    velocity: PointDirection { x: 65; xVariation: 25; y: -8; yVariation: 8 }
  }
}
