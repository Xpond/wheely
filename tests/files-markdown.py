#!/usr/bin/env python3
"""Exercise production Markdown previews through the native GPU renderer, not offscreen software."""
import json
import os
from pathlib import Path
import resource
import shutil
import struct
import subprocess
import tempfile
import qslog

repo = Path(__file__).resolve().parents[1]
plugin = repo / "plugins/xpo.files"
shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
# An older preview can be supplied to verify this check catches the original renderer crash.
source = Path(os.environ.get("WHEELY_MARKDOWN_PREVIEW", plugin / "FilesPreview.qml"))

with tempfile.TemporaryDirectory(prefix="wheely-markdown-") as temporary:
    base = Path(temporary)
    (base / "Commons").symlink_to(shell / "Commons")
    shutil.copyfile(plugin / "FilesIndex.js", base / "FilesIndex.js")
    (base / "FilesPreview.qml").write_text(qslog.patch(source.read_text(), "  id: root\n",
        "  id: root\n  readonly property alias testScroller: scroller\n", exactly=True))
    # The preview references this type even when no video is loaded; video playback is not this test.
    (base / "FilesVideo.qml").write_text("import QtQuick\nItem {\n"
        "  signal fullsize(string path, real position)\n  function toggle() {}\n}\n")
    documents = [(repo / name).read_text() for name in ("docs/dev/files.md", "docs/dev/wheel.md")]
    (base / "shell.qml").write_text('''import QtQuick
import Quickshell
import qs.Commons
import "FilesIndex.js" as FilesIndex
Scope {
  id: root
  property var documents: ''' + json.dumps(documents) + '''
  property int document: 0
  property int tick: 0
  property int frames: 0
  property int captures: 0
  function check(ok, message) { if (!ok) throw new Error("FAIL " + message) }
  QtObject {
    id: panel
    property bool editing: false
    property bool dirty: false
    property bool naming: false
    property bool showsMarkdown: true
    property bool showsCode: !showsMarkdown
    property bool showsDiff: false
    property bool showsDir: false
    property bool showsImage: false
    property bool showsVideo: false
    property var dirColumns: []
    property var dirMarks: []
    property var settledSel: null
    property var sel: null
    property string previewNote: ""
    property int gutterGap: 16
    property int dirTopPad: 7
    property int lineHeight: 24
    property color hoverFill: "transparent"
    property string shownText: root.documents[root.document]
    property int shownLines: 40
    readonly property string previewText: FilesIndex.head(shownText, shownLines)
    readonly property bool previewCut: previewText !== shownText
    readonly property string previewBody: showsMarkdown
      ? FilesIndex.airOut(FilesIndex.escapeTags(FilesIndex.flattenLinks(previewText)))
      : FilesIndex.styledCode(previewText)
    function showAll() { shownLines = shownText.split("\\n").length }
    function previewEntry(column, line) { return null }
    function pickPreview(column, line) {}
    function openPicked() {}
  }
  Window {
    id: window
    width: 740; height: 740; visible: true; color: "#181828"
    title: "Wheely Markdown regression test"
    onFrameSwapped: root.frames++
    FilesPreview { id: preview; anchors.fill: parent; anchors.margins: 20; panel: panel }
  }
  function layer(enabled) {
    var view = preview.testScroller
    root.check(view.layer.enabled === enabled, "wrong layer state")
    root.check(view.width <= window.width && view.height <= window.height, "layer exceeds viewport")
    // An unset textureSize uses the item's dimensions; never allocate the full document's height.
    var size = view.layer.textureSize
    root.check((size.width <= 0 || size.width <= view.width)
      && (size.height <= 0 || size.height <= view.height), "document-sized layer texture")
  }
  function capture() {
    var view = preview.testScroller, name = root.document + "-" + root.tick
    var width = Math.round(view.width), height = Math.round(view.height)
    root.check(view.contentHeight > view.height, "fixture does not scroll")
    view.grabToImage(function (result) {
      root.check(result.saveToFile("''' + str(base) + '''/" + name + ".png"), "capture failed")
      console.log("CAPTURE", name, width, height)
      root.captures++
    })
  }
  Timer {
    interval: 16; running: true; repeat: true
    onTriggered: {
      try {
        root.tick++
        preview.scrollBy(100)
        if (root.tick === 60) { window.width = 940; window.height = 600 }
        if (root.tick === 100) {
          root.check(panel.shownLines > 40 && root.frames > 5, "no growth or rendered frames")
          root.layer(true); root.capture()
        }
        if (root.tick === 105) {
          root.check(root.captures === root.document * 2 + 1, "Markdown frame not captured")
          preview.keepPlace(); preview.editorText = panel.shownText; panel.editing = true
        }
        if (root.tick === 110) { root.layer(false); panel.editing = false }
        if (root.tick === 130) { root.layer(true); panel.showsMarkdown = false }
        if (root.tick === 140) { root.layer(false); panel.showsMarkdown = true }
        if (root.tick === 150) {
          preview.resetScroll(); panel.shownLines = 40
          window.width = 620; window.height = 850
        }
        if (root.tick === 240) {
          root.check(panel.shownLines > 40, "preview did not grow again")
          root.layer(true); root.capture()
        }
        if (root.tick === 300) {
          root.check(root.captures === (root.document + 1) * 2, "frames not captured")
          if (root.document === root.documents.length - 1) {
            console.log("PASS", root.frames, "frames"); Qt.quit(); return
          }
          root.document++; root.tick = 0
          preview.resetScroll(); panel.shownLines = 40
        }
      } catch (error) { console.error(String(error)); Qt.exit(1) }
    }
  }
}
''')
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               QSG_RENDER_LOOP="threaded", QSG_RHI_BACKEND="opengl", QSG_INFO="1",
               QS_DISABLE_CRASH_HANDLER="1", QT_SCALE_FACTOR="1", XDG_CACHE_HOME=str(base / "cache"))
    env.pop("QT_QUICK_BACKEND", None)
    # Off Hyprland's socket: Commons connects to it, and the window opening before its workspaces load
    # is a warning that fails the log check. Nothing rendered here reads Hyprland.
    env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)

    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "shell.qml")],
                            env=env, capture_output=True, text=True, timeout=35, preexec_fn=no_core)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "DEBUG qml: PASS" in log, f"exit {result.returncode}\n{log}"
    qslog.check(log, r"\$HYPRLAND_INSTANCE_SIGNATURE is unset")
    assert "threaded render loop" in log and "backend OpenGL" in log, log
    captures = [line.split("CAPTURE ", 1)[1].split() for line in log.splitlines() if "CAPTURE " in line]
    assert len(captures) == 4, log
    for name, width, height in captures:
        actual = struct.unpack(">II", (base / (name + ".png")).read_bytes()[16:24])
        assert actual == (int(width), int(height)), (name, actual, width, height)
    print("ok: native Markdown scrolls, grows, resizes and switches modes with viewport-sized layers")
