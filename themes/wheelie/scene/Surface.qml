pragma ComponentBehavior: Bound

import QtQuick
import Quickshell.Io

// The baked scene, cropped to fill, with each wheel turning over its plate and under its cover.
Item {
  id: root
  property bool running: true
  property int revolution: 1200
  property real seconds
  property real stormSeconds
  property double previous: Date.now()
  property double nextStorm: Date.now() + 500
  readonly property real wheelTurn: (seconds * 1000 / revolution) % 1
  property var layout: ({ size: [1, 1], wheels: {} })
  readonly property real dpr: Screen.devicePixelRatio || 1
  readonly property size nativeSize: Qt.size(Math.max(1, Math.ceil(width * dpr)), Math.max(1, Math.ceil(height * dpr)))

  // One 16 ms clock: an animation would redraw at the display's own rate.
  onRunningChanged: { previous = Date.now(); nextStorm = previous + 500 }
  Timer {
    interval: 16; repeat: true; running: root.running
    onTriggered: {
      const now = Date.now()
      root.seconds += Math.min(0.2, (now - root.previous) / 1000)
      root.previous = now
      // Regrade the slowly moving storm on this tick, avoiding a separate presentation.
      if (now >= root.nextStorm) {
        root.stormSeconds = root.seconds
        root.nextStorm = now + 500
      }
    }
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
    sourceComponent: Item {
      // Cache the finished grade too: layer.effect otherwise runs on every moving frame.
      // Keep both textures at native pixels, and leave wheels and dust outside the cache.
      Item {
        id: background
        anchors.fill: parent
        layer.enabled: true
        layer.textureSize: root.nativeSize
        Item {
          id: view
          anchors.fill: parent
          layer.enabled: true
          layer.smooth: true
          layer.textureSize: root.nativeSize
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
              decode: scene.decode; seconds: root.stormSeconds
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
          }
        }
      }
      Item {
        width: scene.width; height: scene.height
        transformOrigin: Item.TopLeft
        x: scene.x; y: scene.y; scale: scene.scale
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
              property vector4d rect: Qt.vector4d(axle.x / scene.width, axle.y / scene.height,
                                                  width / scene.width, height / scene.height)
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
              sourceComponent: ShaderEffect {
                readonly property var chain: root.layout.chain
                width: chain.box[2]; height: chain.box[3]
                // The wheel's clock advances the links, one pitch per tooth.
                property real frame: Math.floor((root.wheelTurn * chain.teeth % 1) * chain.frames)
                property vector2d grid: Qt.vector2d(chain.columns, Math.ceil(chain.frames / chain.columns))
                property vector4d rect: Qt.vector4d(chain.box[0] / scene.width, chain.box[1] / scene.height,
                                                    width / scene.width, height / scene.height)
                property var source: Image { source: "chain-motion.png"; visible: false; smooth: true }
                fragmentShader: Qt.resolvedUrl("chain-light.frag.qsb")
              }
            }
            LitImage {
              image: axle.modelData + "-cover.png"
              x: axle.wheel.box[0] - parent.x; y: axle.wheel.box[1] - parent.y
              width: axle.wheel.box[2]; height: axle.wheel.box[2]
              decoded: Qt.size(axle.decoded, axle.decoded)
              rect: Qt.vector4d(axle.wheel.box[0] / scene.width, axle.wheel.box[1] / scene.height,
                                width / scene.width, height / scene.height)
            }
          }
        }

        // Tight contact shadow with a soft falloff, over the sand cover and under the dust.
        LitImage {
          readonly property var rear: root.layout.wheels.rear
          image: "contact-shadow.svg"
          x: rear ? rear.center[0] - 240 : 0
          y: rear ? rear.contactY - 12 : 0
          width: source.implicitWidth; height: source.implicitHeight
          visible: !!rear
          rect: Qt.vector4d(x / scene.width, y / scene.height, width / scene.width, height / scene.height)
        }

        AmbientDust {
          anchors.fill: parent
          seconds: root.seconds
          rear: root.layout.wheels.rear
          sand: Qt.lighter(root.layout.dust, 1.08)
        }
      }
    }
  }
}
