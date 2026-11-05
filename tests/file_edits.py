"""Protect full file contents through the production editor and save verification."""
import json
from pathlib import Path
import re


def check(source, base, run, block):
    preview = (Path(__file__).resolve().parents[1] / "plugins/xpo.files/FilesPreview.qml").read_text()
    dirty_handler = re.search(r"^ +onTextChanged: .*", preview, re.M)[0]
    editable = re.search(r"^  readonly property bool editable:.*?root.settledSel.size === 0\)",
                         source, re.M | re.S)[0]
    production = "\n".join([editable, block(source, r"  function edit\("),
                               block(source, r"  property var saving:"),
                               block(source, r"  function leaveEdit\("),
                               block(source, r"  FileView {\n    id: previewFile")])
    common = '''
  property string previewPath: ""
  property string editedPath: ""
  property string fullText: ""
  property bool utf8: false
  property bool rewrites: false
  property int previewLimit: 64
  function showAll() {}
  property var settledSel: ({ size: 0 })
  property bool editing: false
  property bool dirty: false
  property bool saveError: false
  property bool discarding: false
  property int flashes: 0
  property int focusCalls: 0
  readonly property var panel: root
  QtObject { id: ops; property string fileNote: ""; function note(text) { fileNote = text } }
  TextEdit {
    id: preview
    property alias editorText: preview.text
    function keepPlace() {}
    function focusEditor() { root.focusCalls++ }
''' + dirty_handler + '''
  }
  QtObject { id: keys; function forceActiveFocus() {} }
  Timer { id: savedFlash; interval: 1500; onRunningChanged: if (running) root.flashes++ }
  Timer { id: verifySave; interval: 150; onTriggered: previewFile.reload() }
  Timer { id: discardArmed; interval: 2000; onTriggered: root.discarding = false }
  function check(ok, message) { if (!ok) throw new Error("FAIL " + message) }
''' + production

    for name, content, note in [("non-utf8", b"caf\xe9\n", "not UTF-8; preview only"),
                                ("crlf", b"one\r\ntwo\r\n", "text the editor would change; preview only"),
                                ("nbsp", "a\u00a0b\n".encode(), "text the editor would change; preview only"),
                                ("bom", b"\xef\xbb\xbfhello\n", "text the editor would change; preview only")]:
        target = base / (name + ".txt")
        target.write_bytes(content)
        run("edit-refuses-" + name, common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Timer { interval: 200; running: true; onTriggered: {
    try {
      root.check(root.fullText.length > 0, "fixture never loaded")
      root.edit()
      root.check(!root.editable && !root.editing && root.focusCalls === 0, "unsafe preview became editable")
      root.check(ops.fileNote === ''' + json.dumps(note) + ''', "wrong refusal note")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
        assert target.read_bytes() == content

    target = base / "wipe.md"
    target.write_bytes(b"line one\nline two\n")
    run("save-newer-edit-and-discard", common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Timer { interval: 200; running: true; onTriggered: {
    try {
      root.check(root.fullText === "line one\\nline two\\n", "fixture never loaded")
      root.edit()
      root.check(root.editing && preview.editorText === root.fullText && !root.dirty, "edit did not load full text")
      preview.editorText = ""
      root.check(root.dirty, "editing text did not mark the editor dirty")
      root.save()
      root.check(root.checking === "", "empty save was not tracked")
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 500; running: true; onTriggered: {
    try {
      root.check(root.saving === null && root.fullText === "" && !root.dirty && !root.saveError,
                 "clean empty save did not settle cleanly")
      preview.editorText = "saved edit"
      root.save()
      root.check(root.checking === "saved edit\\n", "second save was not tracked")
      preview.editorText = "newer edit"
      root.save()
      root.check(root.checking === "saved edit\\n", "pending save accepted a second write")
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 900; running: true; onTriggered: {
    try {
      root.check(root.saving === null && root.fullText === "saved edit\\n", "second save did not settle")
      root.check(!root.saveError && root.dirty && root.editing && root.flashes === 2,
                 "verification lost the newer edit or reported the wrong save status: "
                 + JSON.stringify([root.saveError, root.dirty, root.editing, root.flashes]))
      root.check(preview.editorText === "newer edit", "verification replaced newer editor text")
      root.leaveEdit()
      root.check(root.editing && root.dirty && root.discarding, "first Escape discarded dirty text")
      root.leaveEdit()
      root.check(!root.editing && !root.dirty && !root.discarding, "second Escape did not discard")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
    assert target.read_bytes() == b"saved edit\n", "pending newer edits must not replace the saved file"

    # A file grown past the limit since it was listed is not read; a save past it still verifies.
    grown, small = base / "grown.log", base / "small.txt"
    grown.write_bytes(b"x" * 99 + b"\n")
    small.write_bytes(b"small\n")
    run("grown-file-not-read", common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(grown)) + '''
  Timer { interval: 200; running: true; onTriggered: {
    try {
      root.check(root.fullText === "" && !root.utf8, "a file past the limit was read")
      root.previewPath = ''' + json.dumps(str(small)) + '''
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 400; running: true; onTriggered: {
    try {
      root.edit(); preview.editorText = "y".repeat(99)
      root.save()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 800; running: true; onTriggered: {
    try {
      root.check(root.saving === null && !root.saveError, "a save past the limit never verified")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
    assert small.read_bytes() == b"y" * 99 + b"\n"

    # The preview moving to another file mid-edit must not carry the edit there.
    other = base / "other.txt"
    other.write_bytes(b"keep me\n")
    run("save-stays-on-edited-file", common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Timer { interval: 200; running: true; onTriggered: {
    try {
      root.edit(); preview.editorText = "edit"
      root.previewPath = ''' + json.dumps(str(other)) + '''
      root.save()
      root.check(root.saving === null && ops.fileNote === "file is gone; not saved", "edit saved into another file")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
    assert other.read_bytes() == b"keep me\n" and target.read_bytes() == b"saved edit\n"

    locked = base / "read-only-directory"
    locked.mkdir()
    target = locked / "keep.txt"
    target.write_bytes(b"original\n")
    locked.chmod(0o555)
    try:
        run("save-write-failure", common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Timer { interval: 200; running: true; onTriggered: {
    try {
      root.check(root.fullText === "original\\n", "fixture never loaded")
      root.edit(); preview.editorText = "unsaved"; root.save()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 700; running: true; onTriggered: {
    try {
      root.check(root.saving === null && root.saveError && root.dirty && root.editing,
                 "failed write was reported clean or left pending")
      root.check(root.fullText === "original\\n" && preview.editorText === "unsaved" && root.flashes === 0,
                 "failed write lost original bytes, unsaved edit, or showed success")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''', expected=(r"QML FileView at @save-write-failure\.qml\[\d+:\d+\]: Write of "
              + re.escape(str(target)) + r" failed: Unknown error when opening file\.$",))
        assert target.read_bytes() == b"original\n"
    finally:
        locked.chmod(0o755)

    # Another writer's change since the edit began is shown and kept; saving again overwrites it.
    target = base / "shared.txt"
    for name, change, note, disk in [
            ("save-conflict-edited", "printf 'theirs\\n' > \"$1\"", "changed on disk; save again to overwrite", b"mine\n"),
            ("save-conflict-replaced", "printf 'theirs\\n' > \"$1.new\" && mv \"$1.new\" \"$1\"",
             "changed on disk; save again to overwrite", b"mine\n"),
            ("save-conflict-removed", "rm \"$1\"", "cannot read the file; not saved", None)]:
        target.write_bytes(b"original\n")
        run(name, common + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Process { id: other; command: ["sh", "-c", ''' + json.dumps(change) + ''', "sh", ''' + json.dumps(str(target)) + '''] }
  Timer { interval: 200; running: true; onTriggered: { root.edit(); preview.editorText = "mine"; other.running = true } }
  Timer { interval: 400; running: true; onTriggered: root.save() }
  Timer { interval: 700; running: true; onTriggered: {
    try {
      root.check(root.saving === null && root.checking === null && root.dirty && root.editing && root.flashes === 0,
                 "a changed file was overwritten or reported saved")
      root.check(ops.fileNote === ''' + json.dumps(note) + ''' && preview.editorText === "mine", "conflict lost the draft or its note")
      ''' + ("root.save()" if disk else "") + '''
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 1100; running: true; onTriggered: {
    try {
      root.check(''' + ("!root.dirty && root.flashes === 1" if disk else "root.flashes === 0") + ''', "saving again did not settle")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
        assert target.read_bytes() == disk if disk else not target.exists(), name

    # A read-back denied after the write ends the save as failed, and saving again once readable succeeds.
    target = base / "denied.txt"
    target.write_bytes(b"original\n")
    run("save-readback-denied", common.replace("id: verifySave; interval: 150", "id: verifySave; interval: 400") + '''
  Component.onCompleted: root.previewPath = ''' + json.dumps(str(target)) + '''
  Process { id: deny; command: ["chmod", "000", ''' + json.dumps(str(target)) + '''] }
  Process { id: allow; command: ["chmod", "644", ''' + json.dumps(str(target)) + '''] }
  Timer { id: denyLater; interval: 100; onTriggered: deny.running = true }
  property bool denied: false
  onSavingChanged: if (saving !== null && !denied) { denied = true; denyLater.start() }
  Timer { interval: 200; running: true; onTriggered: { root.edit(); preview.editorText = "edited"; root.save() } }
  Timer { interval: 900; running: true; onTriggered: {
    try {
      root.check(root.saving === null && root.checking === null && root.saveError && root.dirty && root.editing,
                 "a failed read-back left the save pending or reported it clean")
      root.check(preview.editorText === "edited", "a failed read-back lost the draft")
      allow.running = true
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
  Timer { interval: 1100; running: true; onTriggered: root.save() }
  Timer { interval: 1800; running: true; onTriggered: {
    try {
      root.check(!root.saveError && !root.dirty && root.flashes === 1, "saving again after access returned failed")
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
    assert target.read_bytes() == b"edited\n"
