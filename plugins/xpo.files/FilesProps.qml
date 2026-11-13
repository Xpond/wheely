pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import "FilesIndex.js" as FilesIndex

// The selection's properties, read-only, in the preview's place. A folder's size is the one the
// header already measures; the rest is stat's and file's.
Item {
  id: root
  property var panel: null
  readonly property real labelWidth: Style.font.body * 7

  readonly property var entry: root.visible ? root.panel.settledSel : null
  readonly property string path: root.entry ? root.entry.path : ""
  // stat's type, mode, octal mode, user, group, modified, accessed, born and size; then the MIME
  // type and a link's target.
  property var info: []
  FilesProcess {
    id: inspector
    onFinished: output => root.info = output.split("\n")
  }
  onPathChanged: {
    root.info = []
    inspector.cancel()
    if (root.path) inspector.start(["sh", "-c", 'stat --printf "%F\\n%A\\n%a\\n%U\\n%G\\n%y\\n%x\\n%w\\n%s\\n" -- "$1" '
      + '&& file -b --mime-type -- "$1"; readlink -- "$1"; :', "props", root.path])
  }

  function when(stamp) { return stamp && stamp !== "-" ? stamp.slice(0, 16) : "" }
  readonly property var rows: {
    var e = root.entry, i = root.info
    if (!e) return []
    var link = i[0] === "symbolic link"
    return [
      ["In", FilesIndex.display(FilesIndex.parentOf(e.path), root.panel.home)],
      ["Kind", link ? "link to " + i[10] : e.isDir ? "folder" : i[9] || ""],
      ["Size", e.isDir ? root.panel.folderSize || "measuring…"
               : i[8] ? FilesIndex.humanSize(+i[8]) + "  ·  " + (+i[8]).toLocaleString(Qt.locale(), "f", 0) + " bytes" : ""],
      ["Permissions", i[1] ? i[1] + "  " + i[2] : ""],
      ["Owner", i[3] ? i[3] + ":" + i[4] : ""],
      ["Modified", root.when(i[5])],
      ["Accessed", root.when(i[6])],
      ["Created", root.when(i[7])]
    ].filter(r => r[1])
  }

  Column {
    anchors.fill: parent
    anchors.topMargin: root.panel.dirTopPad
    spacing: Style.spacing.md

    Text {
      width: parent.width
      wrapMode: Text.WrapAnywhere
      textFormat: Text.PlainText
      text: root.entry ? root.entry.name : ""
      color: Commons.Color.accent
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.subtitle
    }

    Repeater {
      model: root.rows
      Row {
        id: line
        required property var modelData
        spacing: Style.spacing.lg

        Text {
          width: root.labelWidth
          text: line.modelData[0]
          color: Commons.Color.menu.text
          opacity: 0.5
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.bodySmall
          anchors.baseline: value.baseline
        }

        Text {
          id: value
          width: root.width - root.labelWidth - Style.spacing.lg
          wrapMode: Text.WrapAnywhere
          textFormat: Text.PlainText
          text: line.modelData[1]
          color: Commons.Color.menu.text
          opacity: 0.9
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.body
        }
      }
    }
  }
}
