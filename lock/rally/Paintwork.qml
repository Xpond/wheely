pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Shapes

// Mask, shaded paint and outlines share focus; body layers take bodyPose, wheels turn separately.
Item {
  id: root
  property Car car

  anchors.fill: parent
  layer.enabled: true
  layer.smooth: true
  layer.effect: ShaderEffect {
    property var source
    property vector2d resolution: Qt.vector2d(root.car.width, root.car.height)
    property vector2d focusHeights: Qt.vector2d(root.car.focusHeights.x, root.car.focusHeights.y)
    property real amount: root.car.painted
    fragmentShader: Qt.resolvedUrl("car-focus.frag.qsb")
  }

  component Stroke: ShapePath {
    property alias paths: polylines.paths
    fillColor: "transparent"
    capStyle: ShapePath.RoundCap
    joinStyle: ShapePath.RoundJoin
    PathMultiline { id: polylines }
  }

  component Far: Stroke { strokeColor: root.car.settle(0.35, root.car.gapColor, 0.2); strokeWidth: root.car.base * 0.7 }
  component Fine: Stroke { strokeColor: root.car.settle(0.6, root.car.gapColor, 0.3); strokeWidth: root.car.base * (0.8 - 0.1 * root.car.painted) }
  component Panel: Stroke { strokeColor: root.car.settle(0.85, root.car.gapColor, 0.45); strokeWidth: root.car.base * (1 - 0.2 * root.car.painted) }
  component Outline: Stroke { strokeColor: root.car.settle(1, root.car.lineColor, 0.35); strokeWidth: root.car.base * (1.5 - 0.8 * root.car.painted) }
  component Glow: Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.18); strokeWidth: root.car.base * 5 }
  component Tail: Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.35); strokeWidth: root.car.base * 1.2 }
  component Middle: Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.7); strokeWidth: root.car.base * 1.6 }
  component Head: Stroke { strokeColor: root.car.glowColor; strokeWidth: root.car.base * 2.2 }

  component Ink: Shape {
    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
  }
  component BodyInk: Ink { transform: Matrix4x4 { matrix: root.car.bodyPose } }

  // Sliding a clip avoids retessellation; lift it before the drive-off moves beyond the parked span.
  // Zero opacity retains the shapes before painting starts.
  component Coat: Shape {
    width: root.car.coating ? root.car.front : root.car.width
    height: root.car.height
    clip: root.car.coating
    opacity: root.car.painted > 0 ? 1 : 0
    preferredRendererType: Shape.CurveRenderer
  }
  component BodyCoat: Coat { transform: Matrix4x4 { matrix: root.car.bodyPose } }

  // Inside a layer, a Shape cannot clip its own paths; wrap it so the mask stops with the paint.
  component Mask: Item {
    default property alias fills: shape.data
    width: root.car.coating ? root.car.front : root.car.width
    height: root.car.height
    clip: root.car.coating
    opacity: root.car.painted > 0 ? 1 : 0
    Shape {
      id: shape
      width: root.car.width
      height: root.car.height
      // Discrete IDs must not blend at edges: intermediate IDs shade the wrong plane.
      preferredRendererType: Shape.GeometryRenderer
    }
  }
  component BodyMask: Mask { transform: Matrix4x4 { matrix: root.car.bodyPose } }

  component Fill: ShapePath {
    property alias paths: polygons.paths
    strokeColor: "transparent"
    PathMultiline { id: polygons }
  }
  component Cabin: Fill { fillColor: Qt.rgba(15/16, 0, 0, 1) }
  component Paint: Fill { property int tone; fillColor: root.car.paint[tone]; paths: root.car.bodywork[tone] }
  component Inked: Stroke { property int tone; strokeColor: root.car.paint[tone]; strokeWidth: root.car.base * root.car.ink[tone]; paths: root.car.bodywork[tone] }
  component Wheel: Paint { paths: root.car.wheels[tone] }
  component WheelInked: Inked { paths: root.car.wheels[tone] }

  // Mask R encodes surface kind; G encodes top height / 160 or spotlight cans on black plastic.
  // Match the paint's cutouts so glass and wheel wells stay clear.
  Item {
    id: paintPanels
    anchors.fill: parent
    visible: false
    layer.enabled: true
    BodyMask {
      Fill { fillColor: Qt.rgba(1/16, 176/200, 0, 1); paths: root.car.bodywork[64] }
      Fill { fillColor: Qt.rgba(12/16, 0.25, 1, 1); paths: root.car.bodywork[65] }
      Fill { fillColor: Qt.rgba(3/16, 1, 0, 1); paths: root.car.bodywork[62] }
      Fill { fillColor: Qt.rgba(1, 0.5, 0, 1); paths: root.car.bodywork[76] }
    }
    Mask { Fill { fillColor: Qt.rgba(11/16, 0, 0, 1); paths: root.car.wheels[61] } }
    BodyMask {
      Fill { fillColor: Qt.rgba(1, 1, 0, 1); paths: root.car.bodywork[37] }
      Inked { tone: 38; strokeColor: "black" }
      // The cabin, one fill per tone: overlapping tones merged into one path would cancel out.
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[45] }
      Cabin { paths: root.car.bodywork[54] }
      Cabin { paths: root.car.bodywork[46] }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[47] }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[48] }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[50] }
      Cabin { paths: root.car.bodywork[42] }
      Cabin { paths: root.car.bodywork[43] }
      Cabin { paths: root.car.bodywork[44] }
      Cabin { paths: root.car.bodywork[23] }
      Cabin { paths: root.car.bodywork[24] }
      Cabin { paths: root.car.bodywork[25] }
      Inked { tone: 49; strokeColor: Qt.rgba(15/16, 0, 0, 1) }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[51] }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[52] }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[53] }
      Inked { tone: 26; strokeColor: Qt.rgba(15/16, 0, 0, 1) }
      Cabin { fillRule: ShapePath.WindingFill; paths: root.car.bodywork[31] }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(1/16, 0, 0, 1); paths: root.car.bodywork[0] }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(2/16, 0, 0, 1); paths: root.car.bodywork[1] }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(3/16, 85/160, 0, 1); paths: root.car.bodywork[2].slice(0, 1) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(3/16, 133/160, 0, 1); paths: root.car.bodywork[2].slice(1, 2) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(3/16, 101/160, 0, 1); paths: root.car.bodywork[2].slice(2, 3) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(3/16, 51/160, 0, 1); paths: root.car.bodywork[2].slice(3, 4) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(4/16, 0, 0, 1); paths: root.car.bodywork[3].slice(0, 2).concat(root.car.bodywork[3].slice(4)) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(6/16, 0, 0, 1); paths: root.car.bodywork[3].slice(2, 4) }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(7/16, 0, 0, 1); paths: root.car.bodywork[28] }
      Fill { strokeColor: fillColor; strokeWidth: root.car.base; fillColor: Qt.rgba(5/16, 0, 0, 1); paths: root.car.bodywork[4] }
      Fill { fillColor: Qt.rgba(11/16, 0, 0, 1); fillRule: ShapePath.WindingFill; paths: root.car.bodywork[7] }
    }
    Mask {
      Fill { fillColor: Qt.rgba(11/16, 0, 0, 1); fillRule: ShapePath.WindingFill; paths: root.car.wheels[7] }
      Fill { fillColor: Qt.rgba(8/16, 0, 0, 1); paths: root.car.wheels[8] }
      Fill { fillColor: "black"; paths: root.car.wheels[22] }
      WheelInked { tone: 29; strokeColor: Qt.rgba(9/16, 0, 0, 1) }
      Fill { fillColor: Qt.rgba(10/16, 0, 0, 1); paths: root.car.wheels[30] }
      Fill { fillColor: "black"; paths: root.car.wheels[18] }
    }
    BodyMask {
      Fill { fillColor: Qt.rgba(1, 0, 0, 1); paths: root.car.bodywork[34] }
      Inked { tone: 33; strokeColor: "black" }
      Fill { fillColor: "black"; paths: root.car.bodywork[18] }
      // The lamp panel is tone 18's last surface on the body, after the mirror's arm.
      Fill { fillColor: Qt.rgba(12/16, 0, 0, 1); paths: root.car.bodywork[18].slice(-1) }
      Fill { fillColor: Qt.rgba(13/16, 0, 0, 1); paths: root.car.bodywork[6].concat(root.car.bodywork[21]) }
      Fill { fillColor: Qt.rgba(14/16, 0, 0, 1); paths: root.car.bodywork[57] }
      Fill { fillColor: Qt.rgba(12/16, 1, 0, 1); fillRule: ShapePath.WindingFill; paths: root.car.bodywork[58] }
      Fill { fillColor: Qt.rgba(14/16, 0, 0, 1); paths: root.car.bodywork[17] }
      Fill { fillColor: Qt.rgba(13/16, 0, 0, 1); paths: root.car.bodywork[59] }
      Fill { fillColor: "black"; paths: root.car.bodywork[60] }
      // Intake: G=0.4, mesh B=1, reveal B=0.5. Carbon tips: G=0.25, far B=1.
      // Fins encode z = 200G - 100; mirrors/flaps use panel 16, the wing uses top G=1.
      // One fill each: the intake's recess and rear wall overlap, and would cancel in one path.
      Fill { fillColor: Qt.rgba(12/16, 0.4, 0, 1); paths: root.car.bodywork[75] }
      Fill { fillColor: Qt.rgba(12/16, 0.4, 1, 1); paths: root.car.bodywork[73] }
      Fill { fillColor: Qt.rgba(12/16, 0.4, 0.5, 1); paths: root.car.bodywork[74] }
      Fill { fillColor: Qt.rgba(12/16, 0.4, 0.25, 1); paths: root.car.bodywork[72] }
      Fill { fillColor: Qt.rgba(1/16, 24/200, 0, 1); paths: root.car.bodywork[63] }
      Fill { fillColor: Qt.rgba(12/16, 0.25, 0, 1); paths: root.car.bodywork[66] }
    }
  }

  // Shade paint and livery together; glass and outlines keep their own colours.
  Item {
    anchors.fill: parent
    layer.enabled: true
    layer.smooth: true
    layer.effect: ShaderEffect {
      property var source
      property var paintMask: paintPanels
      property var environment: root.car.environment
      property vector2d resolution: Qt.vector2d(root.car.width, root.car.height)
      property real pitch: root.car.pose[0]
      property real shake: root.car.pose[1]
      property real amount: root.car.painted > 0 ? 1 : 0
      fragmentShader: Qt.resolvedUrl("car-paint.frag.qsb")
    }
    // Paint covers construction edges; exposed silhouettes keep their ink.
    BodyInk {
      Panel { paths: root.car.lines[4] }
      Panel { paths: root.car.tracing[4] }
    }
    BodyCoat {
      Paint { tone: 64; strokeColor: Qt.alpha(root.car.gapColor, 0.6); strokeWidth: root.car.base * 0.7 }
      Paint { tone: 65; strokeColor: root.car.paint[67]; strokeWidth: root.car.base * 0.8 }
      Paint { tone: 62; strokeColor: Qt.alpha(root.car.gapColor, 0.6); strokeWidth: root.car.base * 0.7 }
      Paint { tone: 69 }
      Paint { tone: 70 }
      Paint { tone: 71 }
      Paint { tone: 76 }
    }
    Coat { Wheel { tone: 61 } }
    BodyCoat {
      // Bodywork covers the far mirror and cabin except through the windows.
      Paint { tone: 36 }
      Paint { tone: 37 }
      Inked { tone: 38 }
      Paint { tone: 55 }
      Fill {
        // Solid cabin panels: odd-even curve tessellation drops triangles as the body pitches.
        fillRule: ShapePath.WindingFill
        paths: root.car.bodywork[45]
        fillGradient: LinearGradient {
          x1: root.car.cabin[0].x; y1: root.car.cabin[0].y; x2: root.car.cabin[1].x; y2: root.car.cabin[1].y
          GradientStop { position: 0; color: "#b0b2ae" }
          GradientStop { position: 1; color: "#5a5d5a" }
        }
      }
      Paint { tone: 54 }
      Paint { tone: 46 }
      Paint { tone: 47; fillRule: ShapePath.WindingFill }
      Paint { tone: 48; fillRule: ShapePath.WindingFill }
      Paint { tone: 50; fillRule: ShapePath.WindingFill }
      Paint { tone: 42 }
      Paint { tone: 43 }
      Paint { tone: 44 }
      Paint { tone: 23 }
      Paint { tone: 24 }
      Paint { tone: 25 }
      Inked { tone: 49 }
      Paint { tone: 51; fillRule: ShapePath.WindingFill }
      Paint { tone: 52; fillRule: ShapePath.WindingFill }
      Paint { tone: 53; fillRule: ShapePath.WindingFill }
      Inked { tone: 26 }
      Paint { tone: 31; fillRule: ShapePath.WindingFill }
      Paint { tone: 27 }
      Paint { tone: 5 }
      Paint { tone: 56 }
      Paint { tone: 0; strokeColor: fillColor; strokeWidth: root.car.base }
      Paint { tone: 1; strokeColor: fillColor; strokeWidth: root.car.base }
      Paint { tone: 2; strokeColor: fillColor; strokeWidth: root.car.base }
      Paint { tone: 3; strokeColor: fillColor; strokeWidth: root.car.base }
      Paint { tone: 28; strokeColor: fillColor; strokeWidth: root.car.base }
      Paint { tone: 4 }
      Paint { tone: 75 }
      Paint { tone: 72 }
      Paint { tone: 7; fillRule: ShapePath.WindingFill }
    }
    Coat {
      Wheel { tone: 7; fillRule: ShapePath.WindingFill }
      Wheel { tone: 8 }
      Wheel { tone: 22 }
      WheelInked { tone: 29 }
      Wheel { tone: 30 }
    }

    BodyInk {
      Far { paths: root.car.lines[0] }
      Panel { paths: root.car.lines[2] }
      Far { paths: root.car.tracing[0] }
      Panel { paths: root.car.tracing[2] }
    }
    Ink {
      Far { paths: root.car.wheelLines[0] }
      Panel { paths: root.car.wheelLines[2] }
    }

    BodyCoat {
      Paint { tone: 9 }
      Paint { tone: 10 }
      Paint { tone: 11 }
      Paint { tone: 12 }
      Paint { tone: 13 }
      Paint { tone: 32 }
      Paint { tone: 18 }
      // The intake's painted lip stays under the livery.
      Paint { tone: 73 }
      Paint { tone: 74 }
      Paint { tone: 57 }
      Paint { tone: 34 }
      Inked { tone: 33 }
      Paint { tone: 6 }
      Paint { tone: 19 }
      Paint { tone: 20 }
      Paint { tone: 21 }
      Inked { tone: 14 }
      Inked { tone: 15 }
      Inked { tone: 16 }
    }
    Coat {
      Wheel { tone: 18 }
      WheelInked { tone: 15 }
    }

    BodyInk {
      Fine { paths: root.car.lines[1] }
    }
    Ink {
      Fine { paths: root.car.wheelLines[1] }
    }
    // Only the near fin and tip sit in front; the roof and hatch hide the far side.
    BodyCoat {
      Paint { tone: 63; strokeColor: Qt.alpha(root.car.gapColor, 0.6); strokeWidth: root.car.base * 0.7 }
      Paint { tone: 66; strokeColor: root.car.paint[67]; strokeWidth: root.car.base * 0.8 }
    }
    // Paint spotlights over the nose's fine lines so the grille cannot show through them.
    BodyCoat {
      Paint { tone: 58; fillRule: ShapePath.WindingFill }
      Paint { tone: 17; strokeColor: Qt.alpha(root.car.gapColor, 0.6); strokeWidth: root.car.base * 0.7 }
      Paint { tone: 59 }
      Paint { tone: 60 }
    }
  }

  BodyInk {
    Outline { paths: root.car.lines[3] }
  }
  Ink {
    Outline { paths: root.car.wheelLines[3] }
  }
  // Paint wipers over their fine lines.
  BodyCoat {
    Inked { tone: 40 }
    Inked { tone: 41 }
  }
  BodyInk {
    Fine { paths: root.car.tracing[1] }
    Outline { paths: root.car.tracing[3] }
    Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.3 * root.car.lamps); strokeWidth: root.car.base * 8; paths: root.car.glowing }
    Stroke { strokeColor: Qt.alpha(root.car.glowColor, root.car.lamps); strokeWidth: root.car.base * 1.8; paths: root.car.glowing }
    Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.22); strokeWidth: root.car.base * 7; paths: root.car.wavefront }
    Stroke { strokeColor: Qt.alpha(root.car.glowColor, 0.85); strokeWidth: root.car.base * 1.6; paths: root.car.wavefront }
    Glow { paths: root.car.comets[2] }
    Tail { paths: root.car.comets[0] }
    Middle { paths: root.car.comets[1] }
    Head { paths: root.car.comets[2] }
  }
  Ink {
    Glow { paths: root.car.streaks[2] }
    Tail { paths: root.car.streaks[0] }
    Middle { paths: root.car.streaks[1] }
    Head { paths: root.car.streaks[2] }
  }
}
