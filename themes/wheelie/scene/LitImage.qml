import QtQuick

// A still image with the scene's grade, sampled straight to the screen as a plain Image is.
ShaderEffect {
  required property vector4d rect // Its left, top, width, and height in the scene.
  property alias image: picture.source
  property alias decoded: picture.sourceSize
  property vector4d sceneRect: Qt.vector4d(-rect.x / rect.z, -rect.y / rect.w, 1 / rect.z, 1 / rect.w)
  property vector4d crop: Qt.vector4d(0, 0, 1, 1)
  property var source: Image { id: picture; visible: false; smooth: true; cache: false }
  fragmentShader: Qt.resolvedUrl("scene-light.frag.qsb")
}
