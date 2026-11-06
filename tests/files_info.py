"""What Files tells about an entry without opening it: a folder's size, Properties, a hovered name."""
import grp
import json
import os
import pwd


def check(files, base, run, block):
    # Part of a folder unreadable makes du's size a lower bound.
    tree = base / "sized"
    (tree / "locked").mkdir(parents=True)
    (tree / "data").write_bytes(b"x" * 5000)
    run("folder-size", '''
''' + block(files, r"  property string folderSize") + '''
  Timer { interval: 100; running: true; onTriggered: {
    sizer.start(["sh", "-c", 'chmod 000 "$1/locked"; du -sbx -- "$1"; s=$?; chmod 755 "$1/locked"; exit $s', "t", ''' + json.dumps(str(tree)) + '''])
    measured.start()
  } }
  Timer { id: measured; interval: 600; onTriggered: {
    if (root.folderSize.indexOf("≥ ") !== 0) { console.error("FAIL an unreadable part gave", root.folderSize); Qt.exit(1); return }
    console.log("PASS"); Qt.quit()
  } }
''')

    # Selecting folders: a linked one measures its target, a reload around the same one leaves du's
    # walk be, and one seen again shows its last size at once, before du measures it anew.
    (base / "sized-link").symlink_to("sized")
    (base / "sized-other").mkdir()
    run("folder-size-cache", '''
  property string settledPath: ""
  property var settledSel: null
  property bool props: false
  property int shownLines: 0
  property string diffText: ""
  property string imageDims: ""
  property var dirEntries: []
  function readDiff() {}
  function childEntries() { return [] }
  QtObject { id: preview; property int paneHeight: 100; function resetScroll() {} }
  QtObject { id: measurer; function cancel() {} }
''' + block(files, r"  property string folderSize") + block(files, r"^  function media\(")
      + block(files, r"^  onSettledSelChanged: \{").replace("Style.font.subtitle", "16") + '''
  function pick(name) { root.settledSel = { name: name, path: ''' + json.dumps(str(base)) + ''' + "/" + name, isDir: true } }
  function fail(why) { console.error("FAIL", why); Qt.exit(1) }
  property string first: ""
  Timer { interval: 100; running: true; onTriggered: { root.pick("sized-link"); other.start() } }
  Timer { id: other; interval: 600; onTriggered: {
    root.first = root.folderSize
    if (!/^[\\d.]+K$/.test(root.first)) return root.fail("a linked folder measured " + root.first)
    root.pick("sized-link")
    if (sizer.current) return root.fail("a reload around the same folder measured it again")
    root.pick("sized-other")
    if (root.folderSize) return root.fail("another folder showed the last one's size")
    back.start()
  } }
  Timer { id: back; interval: 600; onTriggered: {
    root.pick("sized-link")
    if (root.folderSize !== root.first) return root.fail("a folder seen again showed " + root.folderSize)
    console.log("PASS"); Qt.quit()
  } }
''')

    # Properties read the real file, folder and link: kind, exact size, mode, owner and dates.
    (base / "props.txt").write_text("hello\n")
    (base / "props.txt").chmod(0o640)
    link = base / "props-link"
    link.symlink_to("props.txt")
    run("props-card", '''
  property var settledSel: ({ name: "props.txt", path: ''' + json.dumps(str(base / "props.txt")) + ''', isDir: false })
  property string home: ''' + json.dumps(str(base)) + '''
  property string folderSize: "12K"
  property int dirTopPad: 0
  FloatingWindow { visible: true; implicitWidth: 500; implicitHeight: 400; FilesProps { id: props; anchors.fill: parent; panel: root } }
  function shown() { return props.rows.reduce((o, r) => (o[r[0]] = r[1], o), {}) }
  function fail(why) { console.error("FAIL", why, JSON.stringify(props.rows)); Qt.exit(1) }
  Timer { interval: 500; running: true; onTriggered: {
    var r = root.shown()
    if (r.Kind !== "text/plain" || r.Size !== "6B  ·  6 bytes" || r.Permissions !== "-rw-r-----  640"
        || r.Owner !== ''' + json.dumps(pwd.getpwuid(os.getuid()).pw_name + ":" + grp.getgrgid(os.getgid()).gr_name) + '''
        || !/^\\d{4}-\\d\\d-\\d\\d \\d\\d:\\d\\d$/.test(r.Modified) || r.In !== "~") return root.fail("a file showed")
    root.settledSel = { name: "props-link", path: ''' + json.dumps(str(link)) + ''', isDir: false }
    linked.start()
  } }
  Timer { id: linked; interval: 500; onTriggered: {
    if (root.shown().Kind !== "link to props.txt") return root.fail("a link showed")
    root.settledSel = { name: "sized", path: ''' + json.dumps(str(tree)) + ''', isDir: true }
    folder.start()
  } }
  Timer { id: folder; interval: 500; onTriggered: {
    var r = root.shown()
    if (r.Kind !== "folder" || r.Size !== "12K") return root.fail("a folder showed")
    console.log("PASS"); Qt.quit()
  } }
''', expected=(r"does not support setting window masks",))

    # Hovering a row pops its name up whole after a moment, over the preview's side too when it is cut
    # short, and a short one too; moving to another row hides the first at once. A wheel scroll under a
    # still pointer shows the name of the row now under it, where that row is.
    long = "a-very-long-file-name-that-the-narrow-list-must-cut-short.txt"
    run("hover-name", '''
  property var rows: Array.from({ length: 20 }, (_, i) => ({ name: i === 1 ? "short" : i + ''' + json.dumps(long) + ''', path: "/t/" + i, isDir: false, size: 1 }))
  property int index: 0
  property int rowHeight: 30
  property string pending: ""
  property string naming: ""
  property bool editing: false
  property string doomed: ""
  property var changes: ({})
  property color activeFill: "blue"
  property color hoverFill: "gray"
  property color danger: "red"
  property var marked: ({})
  property var menu: ({ open: false })
  Pointer { id: pointer }
  Window {
    id: window; width: 800; height: 200; visible: true
    FilesList { id: list; width: 200; height: parent.height; panel: root }
  }
  function tip() {
    var found = null, walk = item => item.children.forEach(c => { if (c.wrapMode === Text.WrapAnywhere) found = c; walk(c) })
    walk(window.contentItem)
    return found
  }
  function fail(why) { console.error("FAIL", why); Qt.exit(1) }
  Timer { interval: 200; running: true; onTriggered: {
    pointer.mouseMove(window.contentItem, 60, 15, -1, Qt.NoButton, Qt.NoModifier)
    if (root.tip() && root.tip().visible) return root.fail("the whole name showed at once")
    waited.start()
  } }
  Timer { id: waited; interval: 700; onTriggered: {
    var t = root.tip()
    if (!t.visible || t.text !== "0" + ''' + json.dumps(long) + ''' || t.width < t.implicitWidth || t.mapToItem(window.contentItem, t.width, 0).x <= 200)
      return root.fail("a name cut short did not show whole")
    pointer.mouseMove(window.contentItem, 60, 45, -1, Qt.NoButton, Qt.NoModifier)
    if (t.visible) return root.fail("leaving the name did not hide it")
    fits.start()
  } }
  Timer { id: fits; interval: 700; onTriggered: {
    if (!root.tip().visible || root.tip().text !== "short") return root.fail("a name that fits did not pop up")
    pointer.mouseWheel(window.contentItem, 60, 45, Qt.NoButton, Qt.NoModifier, 0, -120, -1)
    scrolled.start()
  } }
  Timer { id: scrolled; interval: 1000; onTriggered: {
    var t = root.tip(), i = list.view.indexAt(60, 45 + list.view.contentY), y = t.mapToItem(window.contentItem, 0, t.height / 2).y
    if (!t.visible || t.text !== root.rows[i].name || Math.abs(y - 45) > 15)
      return root.fail("after a scroll the tip showed " + t.visible + " " + t.text.slice(0, 3) + " at " + y + " over row " + i)
    console.log("PASS"); Qt.quit()
  } }
''')

    # A folder's preview pops up a hovered entry's name too, over its line and inside the pane, and
    # hides it on the next entry.
    run("hover-preview", '''
  property var entries: Array.from({ length: 30 }, (_, i) => ({ name: i + ''' + json.dumps(long) + ''', path: "/t/" + i, isDir: false, size: 1, modified: null }))
  property var dirColumns: FilesIndex.columns(root.entries, 10, 120, 400, ({}))
  property var dirMarks: []
  property bool showsDir: true
  property int lineHeight: 20
  property int dirTopPad: 5
  property int gutterGap: 16
  property int shownLines: 10
  property bool editing: false
  property bool showsCode: false
  property bool showsDiff: false
  property bool showsImage: false
  property bool showsVideo: false
  property bool showsMarkdown: false
  property string previewBody: ""
  property string previewNote: ""
  property string previewText: ""
  property var settledSel: null
  property color hoverFill: "gray"
  property var sel: null
  property string naming: ""
  function previewEntry(column, line) { return FilesIndex.columnEntry(root.entries, 10, 120, 400, column, line) }
  Pointer { id: pointer }
  Window { width: 900; height: 400; visible: true; FilesPreview { id: preview; panel: root; anchors.fill: parent } }
  function find(test) { var out = [], walk = item => item.children.forEach(c => { if (test(c)) out.push(c); walk(c) }); walk(preview); return out }
  function tip() { return root.find(c => c.wrapMode === Text.WrapAnywhere)[0] }
  function fail(why) { console.error("FAIL", why); Qt.exit(1) }
  property point at
  property string want: ""
  Timer { interval: 200; running: true; onTriggered: {
    // The last column, nearest the pane's right edge.
    var last = root.dirColumns.length - 1, column = root.find(c => c.text === root.dirColumns[last])[0]
    root.want = root.previewEntry(last, 3).name
    root.at = column.mapToItem(preview, 10, 3 * 20 + 10)
    pointer.mouseMove(preview, root.at.x, root.at.y, -1, Qt.NoButton, Qt.NoModifier)
    waited.start()
  } }
  Timer { id: waited; interval: 700; onTriggered: {
    var t = root.tip(), box = t.parent, p = box.mapToItem(preview, 0, 0)
    if (!box.visible || t.text !== root.want) return root.fail("the hovered entry's name did not pop up: " + t.text)
    if (p.x < 0 || p.x + box.width > preview.width + 1 || Math.abs(p.y + box.height / 2 - root.at.y) > 10)
      return root.fail("the name popped up away from its entry or out of the pane")
    pointer.mouseMove(preview, root.at.x, root.at.y + 20, -1, Qt.NoButton, Qt.NoModifier)
    if (box.visible) return root.fail("the next entry kept the last one's name")
    console.log("PASS"); Qt.quit()
  } }
''')
