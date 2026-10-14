"""Paused frames must survive the same window transfers as Files.popOut()."""
import json
import re
import subprocess
import qslog


def check(base, env, files, clip):
    popout = re.search(r"^  function popOut\(\).*?^  }", files, re.M | re.S).group()
    (base / "windows.qml").write_text('''import QtQuick
import Quickshell
import Quickshell.Wayland
Scope {
  id: root
  property bool opened: true
  property bool windowed: false
  readonly property bool shown: root.opened || root.windowed
  property var shell: null
  property var host: null
  property var openScreen: null
  property var media: null
  property int stage: 0
  property int nativeCalls: 0
  property int pausedAt: 750
  function focusedScreen() { return null }
POPOUT
  function check(ok, message) { if (!ok) { console.error("FAIL", message); Qt.exit(1) } }
  function fullsizeButton(item) {
    if (item.tooltipText === "Open in mpv") return item
    for (var child of item.children) { var button = fullsizeButton(child); if (button) return button }
    return null
  }
  function capture(name, next) {
    root.check(!media.playing && media.position === root.pausedAt, "window transfer moved or resumed paused video")
    root.check(movie.muted && Math.abs(media.audioOutput.volume - 0.35) < 0.001, "window transfer changed audio controls")
    root.stage = -1
    media.videoOutput.grabToImage(function(result) {
      root.check(result.saveToFile(name), "frame capture failed")
      root.stage = next
    })
  }
  PanelWindow {
    id: overlay
    implicitWidth: 800; implicitHeight: 450; visible: root.opened
    WlrLayershell.namespace: "wheely-video-test"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
  }
  FloatingWindow {
    id: pinned
    implicitWidth: 600; implicitHeight: 700; visible: root.windowed
    title: "Wheely video test"
  }
  Item {
    parent: root.windowed ? pinned.contentItem : overlay.contentItem
    anchors.fill: parent
    FilesVideo {
      id: movie
      anchors.fill: parent
      path: CLIP
      onFullsize: root.nativeCalls++
    }
  }
  Pointer { id: pointer }
  Timer { interval: 6000; running: true; onTriggered: { console.error("FAIL timeout", root.stage); Qt.exit(1) } }
  Timer { interval: 200; running: true; repeat: true; onTriggered: {
    switch (root.stage) {
    case 0:
      if (!movie.ready) return
      root.media = Array.from(movie.data).find(c => c.videoOutput !== undefined)
      media.position = root.pausedAt; movie.muted = true; media.audioOutput.volume = 0.35
      root.stage = 1; break
    case 1:
      root.capture("window-before.png", 2); break
    case 2:
      root.popOut(); root.stage = 3; break
    case 3:
      root.check(root.windowed && !root.opened, "popout did not move to its window")
      root.capture("window-pinned.png", 4); break
    case 4:
      root.popOut(); root.stage = 5; break
    case 5:
      root.check(root.opened && !root.windowed, "unpin did not restore the overlay")
      root.capture("window-unpinned.png", 6); break
    case 6:
      movie.anchors.rightMargin = 120; root.stage = 7; break
    case 7:
      root.capture("window-resized.png", 8); break
    case 8:
      media.play(); root.popOut(); root.stage = 9; break
    case 9:
      root.check(media.playing && media.position > root.pausedAt, "pinning interrupted active playback")
      media.pause(); root.pausedAt = media.position
      root.popOut(); root.stage = 10; break
    case 10:
      root.capture("window-after-playback.png", 11); break
    case 11:
      var button = root.fullsizeButton(movie)
      root.check(!!button, "fullsize button missing")
      pointer.mouseDoubleClickSequence(button, button.width / 2, button.height / 2,
                                       Qt.LeftButton, Qt.NoModifier, -1)
      root.check(root.nativeCalls === 1 && !button.enabled && button.iconSpinning,
                 "rapid clicks launched twice or showed no opening feedback")
      root.stage = 12; break
    case 12:
      root.check(root.nativeCalls === 1, "another native launch followed the double click")
      console.log("PASS"); Qt.quit()
    }
  } }
}
'''.replace("POPOUT", popout).replace("CLIP", json.dumps(str(clip))))
    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "windows.qml")],
                            cwd=base, env=env, capture_output=True, text=True, timeout=10)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "PASS" in log, log
    qslog.check(log)
    for path in sorted(base.glob("window-*.png")):
        mean = subprocess.check_output(["identify", "-format", "%[fx:mean]", str(path)], text=True)
        assert float(mean) > 0.05, path.name + " was blank"
    print("ok: paused pin/unpin/resize frames, active playback, and one native launch per double click")
