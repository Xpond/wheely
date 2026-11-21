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

  readonly property int pieceLines: 250
  readonly property real pageStep: scroller.height * 0.9
  readonly property real panStep: Style.space(60)
  readonly property real paneWidth: scroller.width
  readonly property real paneHeight: scroller.height
  readonly property int imageStatus: scrollerImage.status
  readonly property int videoStatus: video.status
  property alias editorText: editor.text
  readonly property string lineNumbers:
    root.panel.editing ? FilesIndex.numbers(editor.text, root.editRows)
    : root.panel.showsDiff ? FilesIndex.diffNumbers(root.panel.previewText)
    : root.panel.showsMarkdown ? "" : FilesIndex.numbers(root.panel.previewText)

  // StyledText sets each line's baseline at its ascent. The rich text it replaced
  // set it 4/5 down a fixed-height line whatever the fonts; keep that placement,
  // which the gutter's numbers share.
  function baselineIn(lineHeight) { return Math.floor(lineHeight * 256 / 5) / 64 }
  // Measured as each layout starts: a binding could still hold the previous font.
  property real codeBaseline: 0
  property real codeAscent: 0
  // Text lays out only once its implicit size is wanted, and baselineOffset needs the layout.
  Text {
    id: probe
    visible: false
    width: implicitWidth
    textFormat: Text.StyledText
    renderType: Text.NativeRendering
  }

  function measure(piece) {
    root.codeBaseline = root.baselineIn(piece.lineHeight)
    probe.font = piece.font
    probe.text = "x"
    root.codeAscent = probe.baselineOffset
  }

  // Printable ASCII is drawn in the code font; anything else may fall back to another.
  // Every line but a piece's last also ends in a line separator drawn in the code font.
  function ascentOf(lines, n) {
    var markup = lines[n]
    if (!/[^\x20-\x7e]|&#(?!(?:32|9|39);)/.test(markup)) return root.codeAscent
    probe.text = markup
    return n < lines.length - 1 ? Math.max(root.codeAscent, probe.baselineOffset)
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
  function toggleMute() { const player = video.item as FilesVideo; if (player) player.muted = !player.muted }

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

  // Where a drag over the text began and where it is, in characters of the code or the Markdown.
  // Ctrl+C copies what lies between. Qt's own selection smeared Markdown's tables and dropped text.
  property int from: -1
  property int to: -1
  // Its first and last, or null; read from both ends at once, as letting go sets one before the other.
  function span() { return root.from < 0 || root.to < 0 ? null : [Math.min(root.from, root.to), Math.max(root.from, root.to)] }
  readonly property string picked: {
    var s = root.span()
    return !s ? "" : root.panel.showsMarkdown ? markdownView.getText(s[0], s[1]) : root.panel.previewText.slice(s[0], s[1])
  }
  function letGo() { root.from = root.to = -1 }
  function pickAt(x, y, extend) {
    var p = pointer.mapToItem(root.panel.showsMarkdown ? markdownView : rendered, x, y)
    var at = root.panel.showsMarkdown ? markdownView.positionAt(p.x, p.y) : root.codeAt(p)
    if (!extend || root.from < 0) root.from = at
    root.to = at
  }

  // Where each line of the previewed code starts; the cut's closing ellipsis is no line of the file.
  readonly property var codeStarts: {
    var s = [0], lines = root.panel.previewText.split("\n")
    for (var i = 0; i < lines.length - (root.panel.previewCut ? 1 : 0); i++) s.push(s[i] + lines[i].length + 1)
    return s
  }
  function lineOf(at) { var n = 0; while (root.codeStarts[n + 1] <= at) n++; return n }
  // Hidden plain text in the code's font: a line of code laid out in it says where a point falls.
  // Copies go through it too, as the editor's do: no argument limit on what Qt's clipboard holds.
  TextEdit {
    id: plain
    visible: false
    textFormat: TextEdit.PlainText
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.subtitle
    renderType: Text.NativeRendering
  }
  function copyPicked() { plain.text = root.picked; plain.selectAll(); plain.copy(); plain.text = "" }
  function layLine(n) { plain.text = root.panel.previewText.slice(root.codeStarts[n], root.codeStarts[n + 1] - 1) }
  function codeAt(p) {
    var n = Util.clamp(Math.floor(p.y / root.panel.lineHeight), 0, root.codeStarts.length - 2)
    root.layLine(n)
    return root.codeStarts[n] + plain.positionAt(p.x, 0)
  }
  function codeX(at) { var n = root.lineOf(at); root.layLine(n); return plain.positionToRectangle(at - root.codeStarts[n]).x }

  // Bands behind the pick, from the text's corner: its first line of code from where it starts, the
  // lines between whole, and its last up to where it ends; or each line of Markdown it covers.
  readonly property var bands: {
    var s = root.span()
    if (!s || s[0] === s[1]) return []
    // Laid out again at another width, Markdown's lines move.
    if (root.panel.showsMarkdown) return markdownView.width > 0 ? root.markdownBands(s[0], s[1]) : []
    var h = root.panel.lineHeight, a = root.lineOf(s[0]), b = root.lineOf(s[1])
    var x0 = root.codeX(s[0]), x1 = root.codeX(s[1]), w = Math.max(rendered.width, scroller.width)
    return a === b ? [{ x: x0, y: a * h, w: x1 - x0, h: h }]
      : [{ x: x0, y: a * h, w: w - x0, h: h }, { x: 0, y: (a + 1) * h, w: w, h: (b - a - 1) * h }, { x: 0, y: b * h, w: x1, h: h }]
  }
  // A line of Markdown ends where the next position falls on another row: there a wrapped line
  // continues, and a paragraph's next begins after its break.
  function markdownBands(from, to) {
    var bands = []
    for (var p = from; p < to;) {
      var a = markdownView.positionToRectangle(p)
      var end = Math.min(to, markdownView.positionAt(markdownView.width, a.y + a.height / 2))
      var wraps = markdownView.positionToRectangle(end).y !== a.y
      var right = markdownView.positionToRectangle(wraps ? end - 1 : end).x
      if (right > a.x) bands.push({ x: a.x, y: a.y, w: right - a.x, h: a.height })
      p = Math.max(p + 1, wraps ? end : end + 1)
    }
    return bands
  }

  // Rows each line of the editor wraps to, from where the next line starts; null when none wraps.
  // Counted after each relayout rather than bound: the numbers set the gutter's width, and so the editor's.
  property var editRows: null
  function countRows() {
    var lines = editor.text.split("\n")
    if (!root.panel.editing || editor.lineCount <= lines.length) { root.editRows = null; return }
    var row = editor.contentHeight / editor.lineCount
    var rows = [], at = 0, top = 0
    for (var i = 0; i < lines.length; i++) {
      at += lines[i].length + 1
      var next = i + 1 < lines.length ? editor.positionToRectangle(at).y : editor.contentHeight
      rows.push(Math.round((next - top) / row))
      top = next
    }
    root.editRows = rows
  }

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
  // Previewed code stays unwrapped and scrolls sideways; the editor wraps to the pane.
  Flickable {
    id: scroller
    // Isolate Markdown batches to avoid the Qt 6.12 scrolling crash.
    // Layer the viewport so the texture stays bounded by the visible pane.
    layer.enabled: root.panel.showsMarkdown && !root.panel.editing
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

    // The text picked to copy, behind it.
    Item {
      visible: !root.panel.editing
      x: content.x + (root.panel.showsMarkdown ? markdownView.x : rendered.x)
      y: content.y
      Repeater {
        model: root.bands
        Rectangle {
          required property var modelData
          x: modelData.x; y: modelData.y; width: modelData.w; height: modelData.h
          color: Util.alpha(Commons.Color.accent, 0.35)
        }
      }
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
        width: scroller.width - (gutter.visible ? gutter.width + content.spacing : 0)
        wrapMode: TextEdit.Wrap
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        renderType: Text.NativeRendering
        onTextChanged: { if (root.panel.editing) root.panel.dirty = true; Qt.callLater(root.countRows) }
        onLineCountChanged: Qt.callLater(root.countRows)
        onCursorRectangleChanged: root.revealCursor()
      }

      // Markdown has its own view: a line height that switched with the format, or a handler
      // per line, made Qt lay out its tables many times slower. A TextEdit, for where a point falls.
      TextEdit {
        id: markdownView
        visible: !root.panel.editing && root.panel.showsMarkdown
        width: scroller.width
        text: root.panel.showsMarkdown ? root.panel.previewBody : ""
        wrapMode: TextEdit.Wrap
        textFormat: TextEdit.MarkdownText
        readOnly: true
        activeFocusOnPress: false
        color: Commons.Color.menu.text
        opacity: 0.92
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.subtitle
        renderType: Text.NativeRendering
      }

      // Code in pieces of pieceLines: one Text lays out its lines in time growing with their square,
      // so End on a coloured 200 KB file froze the preview for a second. The pieces stay, so one whose
      // markup is unchanged keeps its layout as the preview grows.
      Column {
        id: rendered
        visible: !root.panel.editing && !root.panel.showsMarkdown
        readonly property var markup: root.panel.showsCode ? FilesIndex.pieces(root.panel.previewBody, root.pieceLines) : []
        onMarkupChanged: {
          if (pieceList.count > markup.length) pieceList.remove(markup.length, pieceList.count - markup.length)
          markup.forEach((m, i) => i < pieceList.count ? pieceList.setProperty(i, "markup", m) : pieceList.append({ markup: m }))
        }
        ListModel { id: pieceList }
        Repeater {
          model: pieceList
          delegate: Text {
            id: piece
            required property string markup
            readonly property var lines: markup.split("<br>")
            // A piece ending on a blank line still counts it, which StyledText would drop.
            height: piece.lines.length * lineHeight
            text: markup
            color: Commons.Color.menu.text
            opacity: 0.92
            textFormat: Text.StyledText
            font.family: Style.font.menuFamily
            font.pixelSize: Style.font.subtitle
            renderType: Text.NativeRendering
            lineHeightMode: Text.FixedHeight
            lineHeight: root.panel.lineHeight
            onLineLaidOut: function (line) {
              if (line.number === 0) root.measure(piece)
              // Absolute: Text has already lowered the line to the foot of its fixed height.
              line.y = line.number * lineHeight + root.codeBaseline - root.ascentOf(piece.lines, line.number)
            }
          }
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

  // A hovered entry's name pops up whole over it after a moment, as the list's does, kept inside the
  // pane. A row is its glyph, two spaces, then the name.
  readonly property var pointed: hovered.visible ? root.panel.previewEntry(hovered.column.index, hovered.line) : null
  readonly property string pointedPath: root.pointed ? root.pointed.path : ""
  property string tipped: ""
  onPointedPathChanged: { root.tipped = ""; if (root.pointedPath) tipWait.restart() }
  Timer { id: tipWait; interval: 500; onTriggered: root.tipped = root.pointedPath }
  TextMetrics {
    id: nameAt
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.subtitle
    text: FilesIndex.DIR_GLYPH + "  "
  }
  FilesTip {
    visible: !!root.tipped
    x: !hovered.column ? 0 : Math.max(0, Math.min(root.width - width,
      scroller.x + folderView.x + hovered.column.x + nameAt.advanceWidth - scroller.contentX - pad))
    y: scroller.y + folderView.y + hovered.line * root.panel.lineHeight - scroller.contentY + (root.panel.lineHeight - height) / 2
    maxWidth: root.width
    text: root.pointed ? root.pointed.name : ""
    pixelSize: Style.font.subtitle
  }

  // A click picks the folder entry under it and a double click opens the pick. Over the scroller
  // rather than in it, so the second click counts whatever the pane shows by then. Over text, a drag
  // picks what to copy, and Shift+click extends it.
  MouseArea {
    id: pointer
    readonly property bool overText: root.panel.showsCode || root.panel.showsMarkdown
    anchors.fill: scroller
    enabled: !root.panel.editing && !root.panel.showsVideo
    hoverEnabled: true
    cursorShape: overText ? Qt.IBeamCursor : Qt.ArrowCursor
    onPressed: mouse => { if (overText) root.pickAt(mouse.x, mouse.y, mouse.modifiers & Qt.ShiftModifier) }
    onPositionChanged: mouse => { if (pressed && overText) root.pickAt(mouse.x, mouse.y, true) }
    onClicked: root.panel.pickPreview(hovered.column ? hovered.column.index : -1, hovered.line)
    onDoubleClicked: root.panel.openPicked()
  }

  // A right-click on an entry of a folder's preview opens that entry's menu where it is, the list left
  // as it was; anywhere else the preview is the selection.
  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.RightButton
    enabled: !root.panel.editing && !root.panel.naming && !!root.panel.sel
    onPressed: mouse => root.panel.menu.openAt(root, mouse.x, mouse.y,
      root.panel.previewEntry(hovered.column ? hovered.column.index : -1, hovered.line) || root.panel.sel)
  }
}
