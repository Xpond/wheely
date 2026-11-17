import QtQuick

// Load first-party panel marks that have no glyph equivalent.
Loader {
  id: root
  property string omarchyPath
  property string file
  property real size
  property color tint
  // An emptied Loader keeps its last item's size, so a reused card would hold a gap for it.
  visible: !!file
  source: file ? omarchyPath + "/shell/plugins/panels/" + file : ""
  Binding { target: root.item; property: "iconSize"; value: root.size }
  Binding { target: root.item; property: "color"; value: root.tint }
}
