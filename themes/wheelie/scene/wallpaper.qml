import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

// The desktop wallpaper: the live scene on every display while Wheelie's animated poster is selected.
Scope {
  id: root
  property bool paused: false
  readonly property string stateDir: Quickshell.env("HOME") + "/.local/state/omarchy/current"
  property string background: ""
  property bool wheelieTheme: false
  readonly property bool animated: wheelieTheme && background.endsWith("/00-wheelie-animated.png")
  onWheelieThemeChanged: backgroundRefresh.restart()

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
      }
    }
  }
  FileView {
    id: themeName
    path: root.stateDir + "/theme.name"
    watchChanges: true
    onFileChanged: reload()
    onLoaded: root.wheelieTheme = text().trim() === "wheelie"
  }

  IpcHandler {
    target: "wheelie"
    function pause(): void { root.paused = true }
    function resume(): void { root.paused = false }
  }

  Variants {
    model: root.animated ? Quickshell.screens : []
    PanelWindow {
      required property var modelData
      screen: modelData
      anchors { top: true; bottom: true; left: true; right: true }
      color: "black"
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}
      WlrLayershell.namespace: "wheelie-wallpaper"
      // Above the shell's static background, beneath normal application windows.
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

      Surface { anchors.fill: parent; running: !root.paused }
    }
  }
}
