pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import qs.Commons as Commons
import "FilesIndex.js" as FilesIndex

// Preview and edit the selected entry through one shared scroller.
Item {
  id: root

  property var panel: null
  clip: true

  readonly property real pageStep: scroller.height * 0.9
  readonly property real panStep: Style.space(60)
  readonly property real paneWidth: scroller.width
  readonly property real paneHeight: scroller.height
  readonly property int imageStatus: scrollerImage.status
  readonly property int videoStatus: video.status
  property alias editorText: editor.text
  readonly property string lineNumbers:
    root.panel.editing ? FilesIndex.numbers(editor.text)
    : root.panel.showsDiff ? FilesIndex.diffNumbers(root.panel.previewText)
    : root.panel.showsMarkdown ? "" : FilesIndex.numbers(root.panel.previewText)

  // StyledText sets each line's baseline at its ascent. The rich text it replaced
  // set it 4/5 down a fixed-height line whatever the fonts; keep that placement,
  // which the gutter's numbers share.
  function baselineIn(lineHeight) { return Math.floor(lineHeight * 256 / 5) / 64 }
  // Measured as each layout starts: a binding could still hold the previous font.
  property real codeBaseline: 0
  property real codeAscent: 0
  property var codeLines: []
  // Text lays out only once its implicit size is wanted, and baselineOffset needs the layout.
  Text {
    id: probe
    visible: false
    width: implicitWidth
    textFormat: Text.StyledText
    renderType: Text.NativeRendering
  }

  function measure(markup) {
    root.codeLines = markup.split("<br>")
    root.codeBaseline = root.baselineIn(rendered.lineHeight)
    probe.font = rendered.font
    probe.text = "x"
    root.codeAscent = probe.baselineOffset
  }

  // Printable ASCII is drawn in the code font; anything else may fall back to another.
  // Every line but the last also ends in a line separator drawn in the code font.
  function ascentOf(n) {
    var markup = root.codeLines[n]
    if (!/[^\x20-\x7e]|&#(?!(?:32|9|39);)/.test(markup)) return root.codeAscent
    probe.text = markup
    return n < root.codeLines.length - 1 ? Math.max(root.codeAscent, probe.baselineOffset)
                                         : probe.baselineOffset
  }

  function scrollBy(dy) {
    scroller.contentY = Util.clamp(scroller.contentY + dy, 0,
                                   Math.max(0, scroller.contentHeight - scroller.height))
  }

  function scrollAcross(dx) {
    scroller.contentX = Util.clamp(scroller.contentX + dx, 0,
                                   Math.max(0, scroller.contentWidth - scroller.width))
  }

  function resetScroll() { scroller.contentY = 0; scroller.contentX = 0 }

  function toggleVideo() { const player = video.item as FilesVideo; if (player) player.toggle() }

  function scrollTo(fraction) {
    // The end of a partly laid out file waits for the rest.
    if (fraction === 1 && root.panel.previewCut) {
      root.pendingAt = 1
      root.panel.showAll()
      return
    }
    scroller.contentY = fraction * Math.max(0, scroller.contentHeight - scroller.height)
    scroller.contentX = 0
  }

  // Preserve relative scroll position while rendered and editable heights change.
  property real pendingAt: -1
  function keepPlace() {
    var at = Util.clamp(scroller.contentY / Math.max(1, scroller.contentHeight - scroller.height), 0, 1)
    // A partly laid out file is only its share of the text.
    root.pendingAt = root.panel.previewCut ? at * root.panel.previewText.length / root.panel.shownText.length : at
  }
  function takePlace() {
    if (root.pendingAt < 0) return
    scroller.contentY = root.pendingAt * Math.max(0, scroller.contentHeight - scroller.height)
    scroller.contentX = 0
    root.pendingAt = -1
    if (root.panel.editing)
      editor.cursorPosition = editor.positionAt(0, Math.max(0, scroller.contentY - root.panel.dirTopPad + 2))
  }

  function focusEditor() { editor.forceActiveFocus() }

  // Lay out more of a long file once the view comes within a screen of its end.
  function fill() {
    if (root.panel.previewCut && !root.panel.editing && scroller.contentY + scroller.height * 2 > scroller.contentHeight)
      root.panel.shownLines *= 2
  }

  function revealCursor() {
    if (!root.panel.editing) return
    var r = editor.cursorRectangle
    var top = content.y + editor.y + r.y
    if (top < scroller.contentY) root.scrollBy(top - scroller.contentY)
    else if (top + r.height > scroller.contentY + scroller.height)
      root.scrollBy(top + r.height - scroller.contentY - scroller.height)
    var left = editor.x + r.x
    if (left < scroller.contentX) root.scrollAcross(left - scroller.contentX - Style.space(40))
    else if (left + r.width > scroller.contentX + scroller.width)
      root.scrollAcross(left + r.width - scroller.contentX - scroller.width + Style.space(40))
  }
  // Keep code unwrapped so line numbers stay aligned.
  Flickable {
    id: scroller
    anchors {
      top: parent.top; bottom: parent.bottom
      left: parent.left; leftMargin: Style.spacing.lg
      right: parent.right; rightMargin: Style.spacing.lg
    }
    visible: root.panel.showsDir || root.panel.showsCode || !!root.panel.previewBody || root.panel.editing
    contentWidth: root.panel.showsDir ? folderView.width : content.width
    // Include both vertical insets so the last line remains reachable.
    contentHeight: (root.panel.showsDir ? folderView.height : content.height)
                   + root.panel.dirTopPad * 2
    onContentHeightChanged: { root.takePlace(); root.fill() }
    onContentYChanged: root.fill()
    flickableDirection: Flickable.HorizontalAndVerticalFlick
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    // The folder entry under the pointer, tinted as the list tints a row. Where it lies is also
    // what a click picks.
    Rectangle {
      id: hovered
      readonly property real px: pointer.mouseX + scroller.contentX - folderView.x
      readonly property real py: pointer.mouseY + scroller.contentY - folderView.y
      readonly property DirColumn column: pointer.containsMouse && root.panel.dirColumns.length && folderView.placed
                                    ? folderView.childAt(px, py) as DirColumn : null
      readonly property int line: Math.floor(py / root.panel.lineHeight)
      visible: !!column && !!root.panel.previewEntry(column.index, line)
      x: folderView.x + (column ? column.x : 0) - root.panel.gutterGap / 2
      y: folderView.y + line * root.panel.lineHeight
      width: (column ? column.width : 0) + root.panel.gutterGap
      height: root.panel.lineHeight
      radius: height / 2
      color: root.panel.hoverFill
    }

    Row {
      id: folderView
      // New columns all sit at x 0 until the Row places them, so the tint looks again after.
      property int placed: 0
      onPositioningComplete: placed++
      visible: root.panel.showsDir
      y: root.panel.dirTopPad
      spacing: root.panel.gutterGap * 2

      // Marks are placed from just past each row's glyph.
      TextMetrics {
        id: glyphWidth
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        text: FilesIndex.DIR_GLYPH
      }

      Repeater {
        model: root.panel.dirColumns

        component DirColumn: Text {
          id: column
          required property string modelData
          required property int index
          text: modelData
          color: Commons.Color.menu.text
          opacity: 0.92
          font.family: Style.font.menuFamily
          font.pixelSize: Style.font.subtitle
          renderType: Text.NativeRendering
          lineHeightMode: Text.FixedHeight
          lineHeight: root.panel.lineHeight

          // git's marks over the room each row keeps after its name, in the list's colour.
          Text {
            x: glyphWidth.advanceWidth
            text: root.panel.dirMarks[column.index] || ""
            color: Commons.Color.accent
            font: column.font
            renderType: Text.NativeRendering
            lineHeightMode: Text.FixedHeight
            lineHeight: root.panel.lineHeight
          }
        }
        delegate: DirColumn {}
      }
    }

    Row {
      id: content
      visible: !root.panel.showsDir
      y: root.panel.dirTopPad
      spacing: root.panel.gutterGap

      Text {
        id: gutter
        visible: root.lineNumbers.length > 0
        text: root.lineNumbers
        horizontalAlignment: Text.AlignRight
        color: Commons.Color.menu.text
        opacity: 0.32
        font.family: Style.font.menuFamily
        // Match the gutter rhythm to editable text or fixed-height preview code.
        font.pixelSize: root.panel.editing ? Style.font.subtitle : Style.font.bodySmall
        renderType: Text.NativeRendering
        lineHeightMode: root.panel.editing ? Text.ProportionalHeight : Text.FixedHeight
        lineHeight: root.panel.editing ? 1.0 : root.panel.lineHeight
        // Left to Qt, the smaller numbers sat above the code's baseline; share it instead.
        onLineLaidOut: function (line) {
          if (!root.panel.editing)
            line.y = line.number * lineHeight + root.baselineIn(lineHeight) - gutterMetrics.ascent
        }
      }
      FontMetrics { id: gutterMetrics; font: gutter.font }

      TextEdit {
        id: editor
        visible: root.panel.editing
        color: Commons.Color.menu.text
        opacity: 0.92
        selectionColor: Util.alpha(Commons.Color.accent, 0.35)
        selectedTextColor: Commons.Color.menu.text
        persistentSelection: true
        textFormat: TextEdit.PlainText
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        renderType: Text.NativeRendering
        onTextChanged: if (root.panel.editing) root.panel.dirty = true
        onCursorRectangleChanged: root.revealCursor()
      }

      // Markdown has its own Text: a line height that switched with the format, or a handler
      // per line, made Qt lay out its tables many times slower.
      Text {
        visible: !root.panel.editing && root.panel.showsMarkdown
        width: scroller.width
        text: root.panel.showsMarkdown ? root.panel.previewBody : ""
        wrapMode: Text.Wrap
        textFormat: Text.MarkdownText
        color: Commons.Color.menu.text
        opacity: 0.92
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        renderType: Text.NativeRendering
      }

      Text {
        id: rendered
        visible: !root.panel.editing && !root.panel.showsMarkdown
        text: root.panel.showsMarkdown ? "" : root.panel.previewBody
        color: Commons.Color.menu.text
        opacity: 0.92
        textFormat: root.panel.showsCode ? Text.StyledText : Text.PlainText
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        renderType: Text.NativeRendering
        lineHeightMode: Text.FixedHeight
        lineHeight: root.panel.lineHeight
        onLineLaidOut: function (line) {
          if (!root.panel.showsCode) return
          if (line.number === 0) root.measure(text)
          // Absolute: Text has already lowered the line to the foot of its fixed height.
          line.y = line.number * lineHeight + root.codeBaseline - root.ascentOf(line.number)
        }
      }
    }
  }

  Rectangle {
    anchors.right: parent.right
    visible: scroller.visible && scroller.contentHeight > scroller.height + 1
    width: Style.space(2)
    radius: width / 2
    color: Util.alpha(Commons.Color.menu.text, 0.22)
    height: Math.max(Style.space(24),
                     scroller.height * scroller.height / Math.max(1, scroller.contentHeight))
    y: (scroller.contentY / Math.max(1, scroller.contentHeight - scroller.height))
       * (scroller.height - height)
  }

  Image {
    id: scrollerImage
    anchors.fill: parent
    // Unsupported or corrupt images fall through to the preview note.
    visible: root.panel.showsImage && status !== Image.Error
    source: root.panel.showsImage ? FilesIndex.fileUrl(root.panel.settledSel.path) : ""
    fillMode: Image.PreserveAspectFit
    asynchronous: true
    sourceSize.width: width
    sourceSize.height: height
  }

  // A fresh player per video: Qt's FFmpeg backend stalls when a playing player changes source.
  Loader {
    id: video
    anchors.fill: parent
    readonly property string path: root.panel.showsVideo ? root.panel.settledSel.path : ""
    onPathChanged: setSource(path ? "FilesVideo.qml" : "", { path: path })
    onLoaded: (item as FilesVideo).fullsize.connect(function(path, position) { root.panel.openVideo(path, position) })
  }

  Text {
    anchors.centerIn: parent
    visible: !!root.panel.previewNote
    text: root.panel.previewNote
    color: Commons.Color.menu.text
    opacity: 0.45
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.bodySmall
  }

  // A click picks the folder entry under it and a double click opens the pick. Over the scroller
  // rather than in it, so the second click counts whatever the pane shows by then.
  MouseArea {
    id: pointer
    anchors.fill: scroller
    enabled: !root.panel.editing && !root.panel.showsVideo
    hoverEnabled: true
    onClicked: root.panel.pickPreview(hovered.column ? hovered.column.index : -1, hovered.line)
    onDoubleClicked: root.panel.openPicked()
  }
}
