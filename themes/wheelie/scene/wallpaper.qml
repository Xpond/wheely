pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

// The desktop wallpaper: the live scene on every display while Wheelie's animated poster is selected.
Scope {
  id: root
  property bool paused: false
  readonly property string stateDir: Quickshell.env("HOME") + "/.local/state/omarchy/current"
  property string background: ""
  property bool wheelieTheme: false
  readonly property bool animated: wheelieTheme && background.endsWith("/00-wheelie-animated.png")

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
        // Setting a theme replaces the folder the link points into; keep the scene meanwhile.
        if (!path) return
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
    onLoaded: {
      const name = text().trim()
      if (!name) return // Omarchy empties the file before writing the new name.
      root.wheelieTheme = name === "wheelie"
      // Another theme has no use for this process; the theme-set hook starts it again.
      if (!root.wheelieTheme) Qt.quit()
    }
  }

  IpcHandler {
    target: "wheelie"
    function pause(): void { root.paused = true }
    function resume(): void { root.paused = false }
    function toggle(): void { root.paused = !root.paused }
  }

  // Hyprland has no IPC events for DPMS or session locks. Refresh in-process,
  // only while this background is selected, so paused displays can wake again.
  Timer {
    interval: 1000; repeat: true; running: root.animated; triggeredOnStart: true
    onTriggered: Hyprland.refreshMonitors()
  }

  Variants {
    model: root.animated ? Quickshell.screens : []
    PanelWindow {
      id: wallpaper
      required property var modelData
      screen: modelData
      readonly property var monitor: Hyprland.monitorFor(screen)
      readonly property var monitorState: monitor ? monitor.lastIpcObject : ({})
      readonly property bool suspended: monitorState.dpmsStatus === false
          || (monitorState.solitaryBlockedBy || []).indexOf("LOCK") >= 0
          // A solitary client is the only window Hyprland draws on this monitor.
          || (!!monitorState.solitary && monitorState.solitary !== "0")
      anchors { top: true; bottom: true; left: true; right: true }
      color: "black"
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}
      WlrLayershell.namespace: "wheelie-wallpaper"
      // Above the shell's static background, beneath normal application windows.
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

      Surface { anchors.fill: parent; running: !root.paused && !wallpaper.suspended }
    }
  }
}
