pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import "FilesIndex.js" as FilesIndex

Item {
  id: root

  property var panel: null

  height: Style.font.title + Style.spacing.controlPaddingY * 2
  clip: true

  // Path, filter and rename share one caret timer.
  property bool caretLit: true
  Timer {
    running: root.panel.shown && (!!root.panel.naming || root.panel.filter.length > 0)
    interval: 530
    repeat: true
    onTriggered: root.caretLit = !root.caretLit
    onRunningChanged: root.caretLit = true
  }

  component Caret: Rectangle {
    width: Style.space(2)
    height: Style.font.subtitle
    color: Commons.Color.accent
    opacity: root.caretLit ? 0.85 : 0.0
  }

  component Separator: Text {
    text: "/"
    color: Commons.Color.menu.text
    opacity: 0.22
    leftPadding: Style.spacing.sm
    rightPadding: Style.spacing.sm
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.subtitle
  }

  // Keep the count beside the path so it cannot be mistaken for preview metadata.
  Row {
    id: trail
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    // Separate the count from the path's trailing caret.
    spacing: Style.spacing.xxl

    Row {
      anchors.verticalCenter: parent.verticalCenter

      Repeater {
        model: root.panel.crumbs

        delegate: Row {
          id: crumb
          required property int index
          required property string modelData

          Separator {
            visible: crumb.index > 0
          }

          Text {
            // The last crumb gives way to everything after it, so the facts never overlap the path.
            width: crumb.index < root.panel.crumbs.length - 1 ? implicitWidth
              : Math.max(0, Math.min(implicitWidth, root.width - parent.x - x - (typed.visible ? typed.width : 0)
                  - (pill.visible ? pill.width + trail.spacing : 0) - count.width - trail.spacing
                  - (facts.visible ? facts.width + trail.spacing : 0)))
            elide: Text.ElideMiddle
            text: crumb.modelData
            color: Commons.Color.menu.text
            // Only the unfinished path segment is active during completion.
            opacity: !root.panel.pathMode && crumb.index === root.panel.crumbs.length - 1 ? 0.95 : 0.5
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.subtitle
          }
        }
      }

      // Completed segments are already in the breadcrumbs.
      Row {
        id: typed
        visible: root.panel.pathMode

        Separator {}

        Text {
          text: root.panel.typedLeaf
          color: Commons.Color.accent
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.subtitle
        }

        Caret { anchors.verticalCenter: parent.verticalCenter }
      }
    }

    // A pill distinguishes the filter even when accent and foreground match.
    Rectangle {
      id: pill
      // Rename uses a separate colour so it cannot be mistaken for filtering.
      visible: !!root.panel.naming || (root.panel.filter.length > 0 && !root.panel.pathMode)
      anchors.verticalCenter: parent.verticalCenter
      width: field.width + Style.spacing.md * 2
      height: Style.font.subtitle + Style.spacing.sm * 2
      radius: height / 2
      color: root.panel.naming ? Util.alpha(Commons.Color.accent, 0.16)
                            : Util.alpha(Commons.Color.menu.text, 0.07)

      // Rename has a movable caret; filtering appends at the end.
      Row {
        id: field
        anchors.left: parent.left
        anchors.leftMargin: Style.spacing.md
        anchors.verticalCenter: parent.verticalCenter

        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: root.panel.naming ? root.panel.renameTo.slice(0, root.panel.renameAt) : root.panel.filter
          color: Commons.Color.accent
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.subtitle
        }

        Caret { anchors.verticalCenter: parent.verticalCenter }

        Text {
          anchors.verticalCenter: parent.verticalCenter
          text: root.panel.naming ? root.panel.renameTo.slice(root.panel.renameAt) : ""
          color: Commons.Color.accent
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.subtitle
        }
      }
    }

    Text {
      id: count
      anchors.verticalCenter: parent.verticalCenter
      text: FilesIndex.countLabel(root.panel.rows.length, root.panel.listedEntries.length,
                                  root.panel.query, root.panel.showHidden, root.panel.order)
      color: Commons.Color.menu.text
      opacity: 0.5
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.bodySmall
    }
  }

  Row {
    id: facts
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
    spacing: Style.spacing.lg
    visible: !!root.panel.settledSel

    Text {
      anchors.verticalCenter: parent.verticalCenter
      visible: root.panel.editing || !!root.panel.fileNote
      text: !root.panel.editing ? root.panel.fileNote
            : root.panel.saveError ? "write failed"
            : root.panel.fileNote ? root.panel.fileNote
            : root.panel.justSaved ? "saved"
            : root.panel.dirty ? "unsaved" : "editing"
      color: root.panel.saveError ? Commons.Color.menu.text : Commons.Color.accent
      opacity: 0.85
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.bodySmall
    }

    // Lines the uncommitted changes add and remove, in the diff's own green and red. They lead
    // the name as one more fact, set off by the facts' own dot and spaces, so no gap of the row's.
    Row {
      anchors.verticalCenter: parent.verticalCenter

      Text {
        readonly property var counts: FilesIndex.diffStat(root.panel.diffText)
        anchors.verticalCenter: parent.verticalCenter
        visible: counts[0] + counts[1] > 0
        textFormat: Text.StyledText
        // No-break spaces: trailing plain ones would not count toward the width.
        text: '<font color="#98c379">+' + counts[0] + '</font>&#32;<font color="#e06c75">\u2212' + counts[1]
              + '</font><font color="' + Util.alpha(Commons.Color.menu.text, 0.5) + '">&#160;&#160;·&#160;&#160;</font>'
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.bodySmall
      }

      Text {
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(implicitWidth, Math.round(root.panel.previewWidth * 0.6))
        elide: Text.ElideMiddle
        text: root.panel.settledSel ? root.panel.settledSel.name : ""
        color: Commons.Color.menu.text
        opacity: 0.9
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.body
      }
    }

    Text {
      anchors.verticalCenter: parent.verticalCenter
      text: root.panel.metaLine
      color: Commons.Color.menu.text
      opacity: 0.5
      font.family: Style.font.menuFamily
      font.pixelSize: Style.font.bodySmall
    }
  }
}
