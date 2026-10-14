import QtQuick
import QtQuick.Layouts
import QtMultimedia
import qs.Commons
import qs.Ui

Rectangle {
  id: root

  property string path: ""
  property bool priming: true
  property bool muted: false
  property bool refreshPending: false
  signal fullsize(string path, int position)
  color: "black"

  readonly property bool ready: !root.priming && player.hasVideo && player.error === MediaPlayer.NoError
    && player.mediaStatus !== MediaPlayer.LoadingMedia
    && player.mediaStatus !== MediaPlayer.NoMedia

  function clock(ms) {
    var s = Math.floor(ms / 1000), m = Math.floor(s / 60), h = Math.floor(m / 60)
    return (h ? h + ":" + String(m % 60).padStart(2, "0") : String(m))
      + ":" + String(s % 60).padStart(2, "0")
  }

  function toggle() {
    if (!root.ready) return
    if (player.playing) player.pause()
    else player.play()
  }

  function openNative() {
    if (handoff.running) return
    handoff.start()
    root.priming = false
    player.pause()
    root.fullsize(root.path, player.position)
  }

  MediaPlayer {
    id: player
    // Encode each path segment so #, %, ?, spaces and Unicode stay literal filenames.
    source: root.path ? "file://" + root.path.split("/").map(encodeURIComponent).join("/") : ""
    videoOutput: video
    audioOutput: AudioOutput { id: audio; volume: 0.7; muted: root.priming || root.muted }
    // Decode one frame silently, then pause, so browsing shows a still preview.
    onMediaStatusChanged: {
      if (mediaStatus !== MediaPlayer.LoadedMedia || !root.priming) return
      if (hasVideo) play()
      else root.priming = false
    }
  }
  onPathChanged: { root.priming = true; handoff.stop(); video.clearOutput() }
  Timer { id: handoff; interval: 1000 }
  // A paused VideoOutput loses its scene graph node when moved to another window.
  // Seek to the same position after the new window renders, to supply its frame again.
  Window.onWindowChanged: root.refreshPending = true
  Connections {
    target: root.Window.window
    function onFrameSwapped() {
      if (!root.refreshPending) return
      root.refreshPending = false
      if (root.ready && !player.playing && player.seekable) player.position = player.position
    }
  }
  Connections {
    target: video.videoSink
    function onVideoFrameChanged() {
      if (!root.priming || video.sourceRect.width <= 0) return
      player.pause()
      root.priming = false
    }
  }
  Component.onDestruction: player.stop()

  VideoOutput {
    id: video
    anchors { top: parent.top; left: parent.left; right: parent.right; bottom: controls.top }
    fillMode: VideoOutput.PreserveAspectFit
    endOfStreamPolicy: VideoOutput.KeepLastFrame
  }

  MouseArea {
    anchors.fill: video
    enabled: root.ready
    cursorShape: Qt.PointingHandCursor
    onClicked: root.toggle()
  }

  Text {
    anchors.centerIn: video
    width: video.width - Style.spacing.lg * 2
    horizontalAlignment: Text.AlignHCenter
    wrapMode: Text.Wrap
    text: player.error !== MediaPlayer.NoError ? "Cannot preview this video · Open in mpv"
      : !root.priming && !player.hasVideo ? "No video track · Open in mpv"
      : !root.ready ? "Loading video…" : ""
    color: "white"
    font.family: Style.font.menuFamily
    font.pixelSize: Style.font.bodySmall
  }

  Rectangle {
    id: controls
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
    height: transport.implicitHeight + Style.spacing.sm * 2
    color: Color.menu.background

    RowLayout {
      id: transport
      anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Style.spacing.sm }
      spacing: Style.spacing.sm

      Button {
        iconText: player.playing ? "󰏤" : "󰐊"
        tooltipText: player.playing ? "Pause" : "Play"
        foreground: Color.menu.text
        enabled: root.ready
        opacity: enabled ? 1 : 0.4
        onClicked: root.toggle()
      }

      Text {
        text: root.clock(seek.dragging ? seek.liveValue : player.position) + " / " + root.clock(player.duration)
        color: Color.menu.text
        font.family: Style.font.menuFamily
        font.pixelSize: Style.font.caption
      }

      PanelSlider {
        id: seek
        Layout.fillWidth: true
        Layout.minimumWidth: Style.space(24)
        value: player.position
        maximum: Math.max(1, player.duration)
        step: 5000
        integer: true
        enabled: root.ready && player.seekable
        opacity: enabled ? 1 : 0.4
        trackColor: Util.alpha(Color.menu.text, 0.18)
        fillColor: Color.accent
        knobColor: Color.menu.text
        onReleased: function(value) { player.position = Math.round(value) }
      }

      Button {
        iconText: root.muted || audio.volume === 0 ? "󰝟" : "󰕾"
        tooltipText: root.muted ? "Unmute" : "Mute"
        foreground: Color.menu.text
        enabled: player.hasAudio
        opacity: enabled ? 1 : 0.4
        onClicked: root.muted = !root.muted
      }

      PanelSlider {
        Layout.preferredWidth: Math.min(Style.space(80), root.width / 6)
        value: audio.volume
        step: 0.05
        enabled: player.hasAudio
        opacity: enabled && !root.muted ? 1 : 0.4
        trackColor: Util.alpha(Color.menu.text, 0.18)
        fillColor: Color.accent
        knobColor: Color.menu.text
        onMoved: function(value) { audio.volume = value; root.muted = false }
      }

      Button {
        iconText: handoff.running ? "󰑐" : "󰊓"
        iconSpinning: handoff.running
        tooltipText: handoff.running ? "Opening mpv…" : "Open in mpv"
        enabled: !handoff.running
        opacity: enabled ? 1 : 0.4
        foreground: Color.menu.text
        onClicked: root.openNative()
      }
    }
  }
}
