#!/usr/bin/env python3
"""Code previews lay out as the editor does: switching between them moves nothing."""
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import qslog

repo = Path(__file__).resolve().parents[1]
plugin = repo / "plugins/xpo.files"
shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
LIMIT = 120

samples = {
    "lead.txt": "\nfoo\nbar\n", "lead2.py": "\n\nx = 1\n", "only-newlines.txt": "\n\n\n",
    "newline.txt": "\n", "one.txt": "x", "blank.py": "a = 1\n\n\n\nb = 2\n",
    "blank-lines.txt": "a\n   \n\t\nb", "trailing.txt": "a   \nb\t\n",
    "crlf.py": "one = 1\r\ntwo = 2\r\n\r\nthree = 3\r\n", "cr.txt": "a\rb\rc\n",
    "fallback.txt": "naïve → 日本語 ✓ 😀\nplain line\n  ✓ indented\n😀\n日本語だけ\n",
    "markup.js": "if (a < b && c > d) { s = \"x\" + 'y' } // &amp; &nbsp; <br> </pre> &#9;\n",
    "separators.txt": "a\u2028b\u2029c\n", "breaks.txt": "a\fb\vc\n\x85d\n",
    "spaces.txt": "nb\u00a0sp ideo\u3000graphic thin\u2009space\n", "control.txt": "bell\x07 esc\x1b[0m\n",
    "long.txt": "x" * 400 + "\ny\n", "tabs.c": "int\tmain(void)\n{\n\tif (x)\n\t\treturn 1;\t// tab\n}\n",
    "multiline.js": "/* multi\n   line */\nconst s = `a\nb`\n",
    "bold.py": "def f():\n    '''doc\n    string'''\n    return 1\n# end",
    "italic.rst": "Title\n=====\n\n*emphasis* and **strong**\n",
    "truncated.txt": "\n".join("line %d" % i for i in range(LIMIT + 30)),
    "blank-cut.sh": "x=1\n" * (LIMIT - 1) + "\ny=2\n",
}
files = [repo / "plugins/xpo.wheel/MenuIndex.js", repo / "plugins/xpo.wheel/Wheel.qml",
         repo / "install.sh", repo / "tests/install.py"]

with tempfile.TemporaryDirectory(prefix="omarchy-preview-") as temporary:
    base = Path(temporary)
    (base / "Commons").symlink_to(shell / "Commons")
    shutil.copyfile(plugin / "FilesIndex.js", base / "FilesIndex.js")
    shutil.copyfile(plugin / "FilesTip.qml", base / "FilesTip.qml")
    styled = (plugin / "FilesPreview.qml").read_text().replace("Style.font.subtitle", "root.panel.codePx")
    styled = styled.replace("  id: root", "  id: root\n  readonly property var testEditor: editor\n  readonly property var testContent: content\n"
                            "  readonly property var testScroller: scroller\n  readonly property var testRendered: rendered\n"
                            "  readonly property var testPointer: pointer\n  readonly property var testPlain: plain", 1)
    # Pieces of three lines, so every case crosses where one piece ends and the next begins.
    size = re.compile(r"pieceLines: \d+")
    assert len(size.findall(styled)) == 1
    (base / "Styled.qml").write_text(size.sub("pieceLines: 3", styled))

    def run(*command):
        return subprocess.run(command, capture_output=True, text=True, check=True).stdout

    # Closing delimiters beyond the requested lines must still inform the lexer, and the cut keeps the
    # lines asked for when a blank one starts the file or ends the cut.
    for name, opening, closing in [("comment.js", "/*", "*/"), ("comment.html", "<!--", "-->"),
                                    ("heredoc.sh", "cat <<EOF", "EOF")]:
        for newline in ["\n", "\r\n"]:
            for lines in [[opening] + ["inside"] * 12, [opening] + ["inside"] * 4 + [""] * 2 + ["inside"] * 6,
                          ["", opening] + ["inside"] * 11]:
                path = base / name
                path.write_text(newline.join(lines + [closing, "after"]), newline="")
                whole = run("python3", str(plugin / "highlight.py"), str(path), "100")
                first = run("python3", str(plugin / "highlight.py"), str(path), "6")
                assert first == "<br>".join(whole.split("<br>")[:6]), (name, repr(newline), lines, first)

    cases = []
    for name, text in list(samples.items()) + [(f.name, f.read_text()) for f in files]:
        # The first lines of a file, not a cut: the editor shows no closing ellipsis.
        text = "\n".join(text.split("\n")[:LIMIT])
        path = base / "cases" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, newline="")
        cases.append({"name": name, "text": text,
                      "styled": run("python3", str(plugin / "highlight.py"), str(path), str(text.count("\n") + 1))})
    (base / "cases.json").write_text(json.dumps(cases))

    # Each case previewed, then edited, in a pane narrow enough to wrap: plain code must draw the same
    # pixels, numbers and all; coloured code, whose colours and weights the editor has not, must start
    # every line at the same height.
    (base / "shell.qml").write_text('''import QtQuick
import Quickshell
import "FilesIndex.js" as FilesIndex
Scope {
  QtObject {
    id: panel
    property int codePx: 13
    property int lineHeight: Math.round(codePx * 1.75)
    property string previewText: ""
    property string fullText: previewText
    property string previewBody: ""
    property bool showsCode: !!previewText
    property bool editing: false
    property bool dirty: false
    property bool previewCut: false
    property bool showsMarkdown: false
    property bool showsDir: false
    property bool showsImage: false
    property bool showsVideo: false
    property bool showsDiff: false
    property var dirColumns: []
    property var settledSel: null
    property string previewNote: ""
    property int gutterGap: 16
    property int dirTopPad: 7
    property color hoverFill: "transparent"
  }
  Window {
    width: 700; height: 600; visible: true; color: "black"
    Styled { id: view; panel: panel; anchors.fill: parent }
  }
  property var jobs: []
  property var failed: []
  // Long enough for Qt to lay out a new case.
  Timer { id: later; interval: 150; property var then; onTriggered: then() }
  function after(then) { later.then = then; later.restart() }
  function grab(name, then) { view.testContent.grabToImage(function (r) { r.saveToFile("out/" + name + ".png"); Qt.callLater(then) }) }
  function next() {
    if (!jobs.length) { console.log(failed.length ? "FAIL " + failed.join("; ") : "PASS"); Qt.quit(); return }
    var j = jobs.shift()
    panel.editing = false
    panel.codePx = j.px
    panel.previewText = j.text
    panel.previewBody = j.stage === "plain" ? FilesIndex.styledCode(j.text) : j.styled
    after(function () {
      var tops = view.codeLayout.tops, height = view.testScroller.contentHeight
      grab(j.file + "-preview", function () {
        view.editorText = j.text
        panel.editing = true
        view.testEditor.cursorVisible = false
        after(function () {
          var e = view.testEditor, lines = j.text.split("\\n"), at = 0
          // The panel never edits text the editor would rewrite.
          if (e.text !== j.text) { console.log("REWRITES " + j.file); Qt.callLater(next); return }
          for (var n = 0; n < lines.length; n++) {
            if (e.positionToRectangle(at).y !== tops[n]) { failed.push(j.file + " line " + (n + 1) + " moves"); break }
            at += lines[n].length + 1
          }
          if (view.testScroller.contentHeight !== height) failed.push(j.file + " height " + height + " to " + view.testScroller.contentHeight)
          grab(j.file + "-editor", next)
        })
      })
    })
  }
  Component.onCompleted: {
    var x = new XMLHttpRequest()
    x.open("GET", Qt.resolvedUrl("cases.json"), false); x.send()
    for (var c of JSON.parse(x.responseText)) for (var px of [11, 13, 16]) for (var stage of ["plain", "coloured"])
      jobs.push({ text: c.text, styled: c.styled, px: px, stage: stage, file: c.name + "-" + px + "-" + stage })
    Qt.callLater(next)
  }
}
''')
    (base / "out").mkdir()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic", QT_FORCE_STDERR_LOGGING="1",
               QML_XHR_ALLOW_FILE_READ="1", XDG_RUNTIME_DIR=str(base / "runtime"), XDG_CACHE_HOME=str(base / "cache"))
    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "shell.qml")], cwd=base,
                            env=env, capture_output=True, text=True, timeout=900)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "PASS" in log, log
    qslog.check(log)

    # compare alone reports 0 for images of different sizes.
    size = lambda p: "%dx%d" % struct.unpack(">II", p.read_bytes()[16:24])
    rewrites = set(re.findall(r"REWRITES (\S+)", log))
    plain = sorted(p.name[:-len("-preview.png")] for p in (base / "out").glob("*-plain-preview.png"))
    plain = [name for name in plain if name not in rewrites]
    assert len(plain) + sum(name.endswith("-plain") for name in rewrites) == len(cases) * 3, len(plain)
    failed = []
    for name in plain:
        a, b = (base / "out" / (name + suffix) for suffix in ("-preview.png", "-editor.png"))
        # Identical files are identical pixels; only a differing pair needs counting.
        diff = "0" if a.read_bytes() == b.read_bytes() else subprocess.run(
            ["magick", "compare", "-metric", "AE", a, b, "null:"], capture_output=True, text=True).stderr.split()[0]
        if size(a) != size(b) or diff != "0":
            failed.append("%s: %s vs %s, %s pixels differ" % (name, size(a), size(b), diff))
    assert not failed, "\n".join(failed)

    # Numbers and code end on the same rows: "line N" and its digits all sit on the baseline.
    def ink_bottoms(image, x0, x1):
        w, h = map(int, size(image).split("x"))
        raw = subprocess.check_output(["magick", image, "-alpha", "extract", "-depth", "8", "gray:-"])
        inked = [any(raw[y * w + x] > 20 for x in range(x0, x1)) for y in range(h)]
        return [y for y in range(h) if inked[y] and (y + 1 == h or not inked[y + 1])]
    for px in (11, 13, 16):
        image = base / "out" / ("truncated.txt-%d-coloured-preview.png" % px)
        assert ink_bottoms(image, 0, 30) == ink_bottoms(image, 60, 200), "%dpx: numbers off their lines" % px

    # Editing from the end of a preview keeps the view where it was, with the cursor in it; editing a
    # shorter file after it draws that file as its preview did; a drag over code picks characters, a bare click
    # picks nothing, and the pick reaches the clipboard.
    (base / "edit.qml").write_text('''import QtQuick
import Quickshell
import "FilesIndex.js" as FilesIndex
Scope {
  QtObject { id: panel; property int codePx: 13; property int lineHeight: Math.round(codePx * 1.75); property string previewText: ""
    property string fullText: previewText; property string previewBody: ""; property bool showsCode: !!previewText
    property bool editing: false; property bool dirty: false
    property bool showsMarkdown: false; property bool showsDir: false; property bool showsImage: false; property bool previewCut: false
    property bool showsVideo: false; property bool showsDiff: false; property var dirColumns: []; property var settledSel: null
    property string previewNote: ""; property int gutterGap: 16; property int dirTopPad: 7; property color hoverFill: "transparent" }
  Window {
    width: 500; height: 400; visible: true
    Styled { id: view; panel: panel; anchors.fill: parent }
    // Reads back what the preview copied.
    TextEdit { id: back; visible: false }
    TextMetrics { id: ruler; font: view.testPlain.font }
  }
  property string long: ''' + json.dumps((repo / "plugins/xpo.wheel/Wheel.qml").read_text()) + '''
  property real end: 0
  Component.onCompleted: Qt.callLater(function () { panel.previewText = root.long; panel.previewBody = FilesIndex.styledCode(panel.previewText); Qt.callLater(atEnd) })
  id: root
  function atEnd() {
    var s = view.testScroller
    s.contentY = root.end = s.contentHeight - s.height
    view.keepPlace(); view.editorText = root.long; panel.editing = true; view.focusEditor()
    settle.start()
  }
  // Where column col of a line of code is drawn, in the pointer's terms.
  function at(col, line) {
    ruler.text = panel.previewText.split("\\n")[line].slice(0, col)
    return view.testRendered.mapToItem(view.testPointer, ruler.advanceWidth, view.codeLayout.tops[line] + 1)
  }
  function drag(a, b, extend) { view.pickAt(a.x, a.y, extend); view.pickAt(b.x, b.y, true); return view.picked }
  property var placed: []
  // Shorter than the first, so the editor's last view of that lies past all of this.
  property string other: ''' + json.dumps((repo / "plugins/xpo.files/FilesList.qml").read_text()) + '''
  function grab(name, then) { view.grabToImage(function (r) { r.saveToFile(name + ".png"); Qt.callLater(then) }) }
  Timer { id: settle; interval: 200; onTriggered: {
      var s = view.testScroller, e = view.testEditor, cursor = view.testContent.y + e.cursorRectangle.y
      root.placed = [s.contentY === root.end, cursor >= s.contentY && cursor + e.cursorRectangle.height <= s.contentY + s.height]
      panel.editing = false; panel.previewText = root.other; panel.previewBody = FilesIndex.styledCode(panel.previewText)
      Qt.callLater(function () { s.contentY = (s.contentHeight - s.height) * 0.8; shown.start() })
  } }
  Timer { id: shown; interval: 200; onTriggered: grab("again-preview", function () {
      view.keepPlace(); view.editorText = root.other; panel.editing = true; view.testEditor.cursorVisible = false
      again.start()
  }) }
  Timer { id: again; interval: 200; onTriggered: grab("again-editor", picking) }
  function picking() {
      panel.editing = false; panel.previewText = "one two three\\nfour five"; panel.previewBody = FilesIndex.styledCode(panel.previewText)
      var word = drag(at(4, 0), at(7, 0), false)
      view.pickAt(at(4, 0).x, at(4, 0).y, false)
      var click = [view.picked, view.bands.length]
      var across = drag(at(4, 0), at(4, 1), true), acrossBands = view.bands.length
      drag(at(4, 0), at(7, 0), false); view.copyPicked(); back.paste()
      var picks = [root.placed, word, click, across, acrossBands, back.text]
      if (JSON.stringify(picks) === JSON.stringify([[true, true], "two", ["", 0], "two three\\nfour", 3, "two"]))
        console.log("PASS")
      else console.log("FAIL", JSON.stringify(picks))
      Qt.quit()
  }
}
''')
    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "edit.qml")], cwd=base,
                            env=env, capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "PASS" in log, log
    qslog.check(log)
    again = [base / ("again-%s.png" % mode) for mode in ("preview", "editor")]
    assert again[0].read_bytes() == again[1].read_bytes() or subprocess.run(
        ["magick", "compare", "-metric", "AE", *again, "null:"], capture_output=True, text=True).stderr.split()[0] == "0", \
        "a second edit is not drawn as its preview was"

    print("ok: %d code previews at three sizes lay out as the editor does, plain ones pixel for pixel;"
          " editing keeps the view, shows the cursor and draws a second file" % len(cases))
