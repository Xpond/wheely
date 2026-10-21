pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Particles
import Quickshell.Io

// The baked scene, cropped to fill, with each wheel turning over its plate and under its cover.
Item {
  id: root
  property bool running: true
  property bool particlesRunning: running
  property int revolution: 1200
  property real wheelTurn
  property var layout: ({ size: [1, 1], wheels: {} })
  readonly property real dpr: Screen.devicePixelRatio || 1

  NumberAnimation on wheelTurn {
    from: 0; to: 1; duration: root.revolution
    loops: Animation.Infinite; paused: !root.running
  }

  FileView {
    path: decodeURIComponent(Qt.resolvedUrl("layout.json").toString().slice(7))
    watchChanges: true
    onFileChanged: reload()
    onLoaded: root.layout = JSON.parse(text())
  }

  // Built once the screen's size and the layout are known, so each image decodes once.
  Loader {
    anchors.fill: parent
    active: root.width > 0 && root.height > 0 && !!root.layout.cutout
    // Light a screen-sized texture, so it reaches the display pixel for pixel.
    sourceComponent: Item {
      id: view
      layer.enabled: true
      layer.smooth: true
      layer.textureSize: Qt.size(Math.max(1, Math.ceil(width * root.dpr)), Math.max(1, Math.ceil(height * root.dpr)))
      layer.effect: ShaderEffect {
        // The scene's rectangle within the view, so the lighting keeps to scene coordinates.
        property vector4d sceneRect: Qt.vector4d(scene.x / view.width, scene.y / view.height,
                                                 scene.width * scene.scale / view.width,
                                                 scene.height * scene.scale / view.height)
        fragmentShader: Qt.resolvedUrl("scene-light.frag.qsb")
      }

      Item {
        id: scene
        width: root.layout.size[0]
        height: root.layout.size[1]
        transformOrigin: Item.TopLeft
        scale: Math.max(root.width / width, root.height / height)
        // Images decode at twice their on-screen pixels, at most native: closest to the native scene.
        readonly property real decode: Math.min(1, 2 * scale * root.dpr)
        // Centered on whole device pixels, so the crop never shifts texels by half a pixel.
        x: Math.round((root.width - width * scale) / 2 * root.dpr) / root.dpr
        y: Math.round((root.height - height * scale) / 2 * root.dpr) / root.dpr

        Image {
          source: "base.png"; smooth: true
          width: parent.width; height: parent.height
          sourceSize: Qt.size(Math.ceil(width * scene.decode), Math.ceil(height * scene.decode))
        }
        // Sized by bindings, not anchors: anchors apply only after the storm image starts loading.
        HorizonStorm {
          width: parent.width; height: parent.height; horizon: root.layout.horizon || 0
          decode: scene.decode; running: root.particlesRunning
        }
        // A white band across each sky print edge, over the storm; the last edge lies past the horizon.
        Item {
          width: parent.width; height: root.layout.horizon || 0
          clip: true
          Repeater {
            model: root.layout.prints || []
            Rectangle {
              required property int modelData
              y: modelData - root.layout.printBorder
              width: parent.width; height: 2 * root.layout.printBorder
              color: "white"
            }
          }
        }
        // Everything but the sky, redrawn over the storm.
        Image {
          source: "cutout.png"
          x: root.layout.cutout[0]; y: root.layout.cutout[1]
          width: root.layout.cutout[2]; height: root.layout.cutout[3]
          sourceSize: Qt.size(Math.ceil(width * scene.decode), Math.ceil(height * scene.decode))
        }
        Repeater {
          model: Object.keys(root.layout.wheels)
          Item {
            id: axle
            required property string modelData
            readonly property var wheel: root.layout.wheels[modelData]
            readonly property int decoded: Math.ceil(wheel.size * scene.decode)
            x: wheel.center[0] - wheel.size / 2; y: wheel.center[1] - wheel.size / 2
            width: wheel.size; height: wheel.size

            ShaderEffect {
              anchors.fill: parent
              property real turn: root.wheelTurn
              property real tireRadius: axle.wheel.radius / axle.wheel.size
              property real exposure: axle.modelData === "rear" ? 0.92 : 1.0
              property var source: Image {
                source: axle.modelData + ".png"
                visible: false
                smooth: true
                sourceSize: Qt.size(axle.decoded, axle.decoded)
              }
              fragmentShader: Qt.resolvedUrl("wheel-light.frag.qsb")
            }
            Loader {
              active: axle.modelData === "rear" && !!root.layout.chain
              x: root.layout.chain ? root.layout.chain.box[0] - parent.x : 0
              y: root.layout.chain ? root.layout.chain.box[1] - parent.y : 0
              sourceComponent: AnimatedSprite {
                source: "chain-motion.png"
                width: root.layout.chain.box[2]; height: root.layout.chain.box[3]
                frameWidth: width; frameHeight: height
                frameCount: root.layout.chain.frames
                paused: true // The wheel's clock advances the links, one pitch per tooth.
                interpolate: false
                currentFrame: Math.floor((root.wheelTurn * root.layout.chain.teeth % 1) * frameCount)
              }
            }
            Image {
              source: axle.modelData + "-cover.png"
              x: axle.wheel.box[0] - parent.x; y: axle.wheel.box[1] - parent.y
              width: axle.wheel.box[2]; height: axle.wheel.box[2]
              sourceSize: Qt.size(axle.decoded, axle.decoded)
            }
          }
        }

        // Tight contact shadow with a soft falloff, over the sand cover and under the dust.
        Image {
          readonly property var rear: root.layout.wheels.rear
          source: "contact-shadow.svg"
          x: rear ? rear.center[0] - 240 : 0
          y: rear ? rear.contactY - 12 : 0
          visible: !!rear
          smooth: true
        }

        // Loose sand lifts briefly, spreads, and settles beside the painted ground trail.
        // Measured in rear-wheel radii so the dust keeps its size at any resolution.
        Loader {
          active: !!root.layout.wheels.rear
          sourceComponent: Item {
            id: spray
            readonly property var rear: root.layout.wheels.rear
            readonly property real r: rear.radius || rear.size / 2
            // Particle colors need premultiplication; the SVG texture is premultiplied by Qt.
            function sand(a) { const c = Qt.lighter(Qt.color(root.layout.dust), 1.08); return Qt.rgba(c.r * a, c.g * a, c.b * a, a) }
            x: rear.center[0]; y: rear.contactY || rear.center[1] + r

            ParticleSystem { id: dust; paused: !root.particlesRunning }
            ImageParticle {
              system: dust; groups: ["grain"]
              source: "dust.svg"
              color: parent.sand(0.4)
              rotationVariation: 180
            }
            ImageParticle {
              system: dust; groups: ["puff"]
              source: "dust.svg"
              color: parent.sand(0.32)
              rotationVariation: 35
              rotationVelocityVariation: 25
              xVector: PointDirection { x: 1.35; y: 0 }
              yVector: PointDirection { x: 0; y: 0.6 }
            }
            Emitter {
              system: dust; group: "grain"
              x: 0.3 * spray.r; y: -0.14 * spray.r; width: 0.2 * spray.r; height: 0.04 * spray.r
              emitRate: 32; lifeSpan: 750; lifeSpanVariation: 200
              size: 0.025 * spray.r; endSize: 0.012 * spray.r; sizeVariation: 0.01 * spray.r
              velocity: AngleDirection { angle: -30; angleVariation: 12; magnitude: 1.8 * spray.r; magnitudeVariation: 0.45 * spray.r }
              acceleration: PointDirection { y: 3 * spray.r }
            }
            // Grains land: none falls through the sand.
            Age { system: dust; groups: ["grain"]; x: -spray.r; y: -0.08 * spray.r; width: 6 * spray.r; height: 2 * spray.r; lifeLeft: 0 }
            Emitter {
              system: dust; group: "puff"
              x: 0.35 * spray.r; y: -0.16 * spray.r; width: 0.4 * spray.r; height: 0.06 * spray.r
              emitRate: 22; lifeSpan: 1600; lifeSpanVariation: 400
              size: 0.28 * spray.r; endSize: 0.9 * spray.r; sizeVariation: 0.12 * spray.r
              velocity: PointDirection { x: 1.5 * spray.r; xVariation: 0.6 * spray.r; y: -0.64 * spray.r; yVariation: 0.14 * spray.r }
              acceleration: PointDirection { y: 0.4 * spray.r }
            }
            Friction { system: dust; groups: ["puff"]; factor: 1 }
          }
        }

        AmbientDust { anchors.fill: parent; running: root.particlesRunning }
      }
    }
  }
}
