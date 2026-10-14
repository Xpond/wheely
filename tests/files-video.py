#!/usr/bin/env python3
"""Native Wayland video frames, pointer controls, file switching and player cleanup."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import qslog
from files_video_window import check as check_video_windows

repo = Path(__file__).resolve().parents[1]
shell = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
files = (repo / "plugins/xpo.files/Files.qml").read_text()
video_property = re.search(r"^  readonly property bool showsVideo:.*\n.*", files, re.M).group()
preview_path = files[files.index("  readonly property string previewPath:"):files.index("  // Keep the full file")]

with tempfile.TemporaryDirectory(prefix="wheely-video-") as temporary:
    base = Path(temporary)
    for name in ["Commons", "Ui"]:
        (base / name).symlink_to(shell / name)
    for name in ["FilesPreview.qml", "FilesVideo.qml", "FilesIndex.js", "FilesKeys.js"]:
        shutil.copyfile(repo / "plugins/xpo.files" / name, base / name)
    (base / "Pointer.qml").write_text("import QtTest\nTestEvent {}\n")
    first = base / "video #?% ' 日本語.MP4"
    second = base / "second.webm"
    broken = base / "broken.mp4"
    audio_only = base / "audio.mp4"
    broken.write_text("not a video")
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=24",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "3", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(first)], check=True, timeout=20)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(first), "-vn", "-c:a", "copy", str(audio_only)],
                   check=True, timeout=20)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=320x180:rate=24",
                    "-t", "2", "-c:v", "libvpx-vp9", str(second)], check=True, timeout=20)
    (base / "shell.qml").write_text('''import QtQuick
import Quickshell
import "FilesIndex.js" as FilesIndex
import "FilesKeys.js" as FilesKeys
Scope {
  id: root
  property var settledSel: ({path: FIRST, name: "video.MP4", size: 100})
  property int previewLimit: 262144
VIDEO_PROPERTY
PREVIEW_PATH
  property bool showsImage: false
  property bool showsDir: false
  property bool showsCode: false
  property bool showsDiff: false
  property bool showsMarkdown: false
  property bool editing: false
  property string naming: ""
  property string filter: "video"
  property int index: 7
  property bool dirty: false
  property bool previewCut: false
  property int lineHeight: 20
  property int dirTopPad: 0
  property int gutterGap: 16
  property var dirColumns: []
  property var dirMarks: []
  property string previewBody: ""
  property string previewNote: ""
  property string previewText: ""
  property string shownText: ""
  property color hoverFill: "gray"
  property var movie: null
  property var media: null
  property var nativeCall: []
  property int stage: 0
  function openVideo(path, position) { root.nativeCall = [path, position] }
  function pickPreview() { check(false, "video click reached folder selection") }
  function openPicked() { check(false, "video click opened the folder pick") }
  function check(ok, message) { if (!ok) { console.error("FAIL", message); Qt.exit(1) } }
  function find(test, item) {
    if (test(item)) return item
    for (var child of item.children) { var match = find(test, child); if (match) return match }
    return null
  }
  function click(item, fraction) {
    check(!!item, "missing control")
    pointer.mouseClick(item, item.width * (fraction === undefined ? 0.5 : fraction), item.height / 2,
                       Qt.LeftButton, Qt.NoModifier, -1)
  }
  function player(item) { return Array.from(item.data).find(c => c.videoOutput !== undefined) }
  function space() {
    var event = {key: Qt.Key_Space, modifiers: Qt.NoModifier, text: " ", isAutoRepeat: false, accepted: false}
    FilesKeys.onKey(root, {doomed: ""}, preview, event)
    root.check(event.accepted && root.filter === "video" && root.index === 7, "Space changed the selection or filter")
  }
  function capture(name, next) {
    media.videoOutput.grabToImage(function(result) {
      check(result.saveToFile(name), "frame capture failed")
      root.stage = next
    })
  }
  Pointer { id: pointer }
  Window {
    width: 800; height: 450; visible: true
    flags: Qt.Tool | Qt.WindowDoesNotAcceptFocus
    FilesPreview { id: preview; anchors.fill: parent; panel: root }
  }
  Timer { interval: 8000; running: true; onTriggered: { console.error("FAIL timeout", root.stage); Qt.exit(1) } }
  Timer { interval: 80; running: true; repeat: true; onTriggered: {
    var loader = root.find(c => c.item !== undefined && c.source !== undefined, preview)
    switch (root.stage) {
    case 0:
      if (!loader || !loader.item || !loader.item.ready) return
      root.movie = loader.item; root.media = root.player(root.movie)
      root.check(!root.previewPath, "small videos entered the text reader")
      root.check(!media.playing && media.position < 150, "initial preview did not pause at the start")
      root.check(movie.clock(3661000) === "1:01:01", "hour-long duration")
      root.stage = -1; root.capture("first.png", 1); break
    case 1:
      root.click(root.find(c => c.tooltipText === "Play", movie))
      root.space(); root.check(!media.playing, "Space did not pause video")
      root.space(); root.check(media.playing, "Space did not resume video")
      root.stage = 2; break
    case 2:
      if (media.position < 200) return
      root.click(root.find(c => c.tooltipText === "Pause", movie))
      root.check(!media.playing, "pause button did not pause")
      root.click(root.find(c => c.maximum === media.duration, movie), 0.65)
      root.check(Math.abs(media.position - media.duration * 0.65) < 100, "timeline did not seek")
      root.click(root.find(c => c.maximum === 1, movie), 0.3)
      root.check(Math.abs(media.audioOutput.volume - 0.3) < 0.03, "volume slider did not change volume")
      root.click(root.find(c => c.tooltipText === "Mute", movie))
      root.check(media.audioOutput.muted, "mute button did not mute")
      root.click(root.find(c => c.tooltipText === "Open in mpv", movie))
      root.check(!media.playing && nativeCall[0] === FIRST && nativeCall[1] > 1500,
                 "fullsize lost the visible path or playback position")
      movie.toggle()
      root.settledSel = ({path: SECOND, name: "second.webm", size: 100}); root.stage = 3; break
    case 3:
      if (!movie.ready || String(media.source).indexOf("second.webm") < 0) return
      root.check(!media.playing && media.position < 150 && !media.hasAudio, "next video retained playback")
      root.stage = -1; root.capture("second.png", 4); break
    case 4:
      movie.toggle()
      root.check(media.playing, "closing did not exercise active playback")
      root.settledSel = null; root.stage = 5; break
    case 5:
      root.check(!loader.item, "leaving a video retained its player")
      root.settledSel = ({path: BROKEN, name: "broken.mp4", size: 10}); root.stage = 6; break
    case 6:
      if (!loader.item || root.player(loader.item).error === 0) return
      root.movie = loader.item; root.media = root.player(movie)
      root.check(!movie.ready, "corrupt video enabled playback")
      root.click(root.find(c => c.tooltipText === "Open in mpv", movie))
      root.check(nativeCall[0] === BROKEN, "corrupt video could not open in mpv")
      root.settledSel = ({path: AUDIO_ONLY, name: "audio.mp4", size: 100}); root.stage = 7; break
    case 7:
      if (!loader.item || loader.item.priming) return
      root.media = root.player(loader.item)
      root.check(!loader.item.ready && !media.playing && !media.hasVideo,
                 "audio-only container started playback without a video frame")
      root.settledSel = null
      console.log("PASS"); Qt.quit()
    }
  } }
}
'''.replace("FIRST", json.dumps(str(first))).replace("SECOND", json.dumps(str(second)))
       .replace("BROKEN", json.dumps(str(broken))).replace("VIDEO_PROPERTY", video_property)
       .replace("AUDIO_ONLY", json.dumps(str(audio_only)))
       .replace("PREVIEW_PATH", preview_path))
    env = dict(os.environ, QT_QPA_PLATFORM="wayland", QT_QPA_PLATFORMTHEME="generic",
               XDG_CACHE_HOME=str(base / "cache"))
    result = subprocess.run(["quickshell", "--no-color", "-p", str(base / "shell.qml")], cwd=base,
                            env=env, capture_output=True, text=True, timeout=12)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and "PASS" in log, log
    qslog.check(log, r"qt.multimedia.*Could not open media")
    for name in ["first.png", "second.png"]:
        mean = subprocess.check_output(["identify", "-format", "%[fx:mean]", str(base / name)], text=True)
        assert float(mean) > 0.05, name + " was blank"
    print("ok: paused MP4/WebM frames, playback, seeking, audio controls, mpv handoff and cleanup")
    check_video_windows(base, env, files, first)
