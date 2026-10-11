import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

Scope {
  id: root
  property bool paused: false
  readonly property string stateDir: Quickshell.env("HOME") + "/.local/state/omarchy/current"
  property string background: ""
  property bool tidalTheme: false
  property string lastStatic: stateDir + "/theme/backgrounds/01-shoreline.jpg"
  readonly property bool muted: background.endsWith("/00-muted-coast-animated.png")
  readonly property bool animated: tidalTheme && (muted || background.endsWith("/00-living-coast-animated.png"))
  onTidalThemeChanged: backgroundRefresh.restart()

  // Watch the directory: watching the image misses replacement of its symlink.
  FileView {
    path: root.stateDir
    preload: false
    watchChanges: true
    onFileChanged: { backgroundRefresh.restart(); themeName.reload() }
  }
  Timer {
    id: backgroundRefresh
    interval: 20
    onTriggered: {
      if (backgroundPath.running) restart()
      else backgroundPath.running = true
    }
  }
  Process {
    id: backgroundPath
    command: ["readlink", "-f", root.stateDir + "/background"]
    running: true
    stdout: StdioCollector {
      onStreamFinished: {
        const path = text.trim()
        if (path !== root.background) root.paused = false
        root.background = path
        if (root.tidalTheme && path && !root.animated) root.lastStatic = path
      }
    }
  }
  FileView {
    id: themeName
    path: root.stateDir + "/theme.name"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: root.tidalTheme = text().trim() === "tidal"
  }

  IpcHandler {
    target: "tidal"
    function stop(): void {
      if (root.animated) Quickshell.execDetached(["omarchy", "theme", "bg", "set", root.lastStatic])
    }
    function pause(): void { root.paused = true }
    function resume(): void { root.paused = false }
  }

  Variants {
    model: root.animated ? Quickshell.screens : []
    PanelWindow {
      required property var modelData
      screen: modelData
      anchors { top: true; bottom: true; left: true; right: true }
      color: "#ECECE8"
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}
      WlrLayershell.namespace: "tidal-wallpaper"
      // Above the shell's static background, beneath normal application windows.
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

      Surface {
        anchors.fill: parent
        muted: root.muted ? 1 : 0
        running: !root.paused
      }
    }
  }
}
