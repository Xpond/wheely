//@ pragma Env QSG_RENDER_LOOP=threaded
pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Hyprland

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
        // Setting a theme replaces the folder the link points into; keep the surfaces meanwhile.
        if (!path) return
        if (path !== root.background) root.paused = false
        root.background = path
        if (root.tidalTheme && !root.animated) root.lastStatic = path
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
      root.tidalTheme = name === "tidal"
      // Another theme has no use for this process; the theme-set hook starts it again.
      if (!root.tidalTheme) Qt.quit()
    }
  }

  IpcHandler {
    target: "tidal"
    function stop(): void {
      if (root.animated) Quickshell.execDetached(["omarchy", "theme", "bg", "set", root.lastStatic])
    }
    function pause(): void { root.paused = true }
    function resume(): void { root.paused = false }
    function toggle(): void { root.paused = !root.paused }
  }

  // Hyprland has no IPC events for DPMS or session locks. Refresh in-process,
  // only while an animated coast is selected, so paused displays can wake again.
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
      readonly property real dpr: contentItem.Screen.devicePixelRatio
      readonly property int fullHeight: screen ? screen.height : 0
      // Keep fractional-scale outputs whole: separate logical windows can straddle device pixels.
      readonly property int movingHeight: dpr === Math.round(dpr) ? Math.ceil(fullHeight * 0.82) : fullHeight
      readonly property bool split: movingHeight < fullHeight
      readonly property var monitor: Hyprland.monitorFor(screen)
      readonly property var monitorState: monitor ? monitor.lastIpcObject : ({})
      readonly property bool suspended: monitorState.dpmsStatus === false
          || (monitorState.solitaryBlockedBy || []).indexOf("LOCK") >= 0
          // A solitary client is the only window Hyprland draws on this monitor.
          || (!!monitorState.solitary && monitorState.solitary !== "0")
      anchors { top: true; bottom: !wallpaper.split; left: true; right: true }
      implicitHeight: movingHeight
      color: "#ECECE8"
      exclusionMode: ExclusionMode.Ignore
      mask: Region {}
      WlrLayershell.namespace: "tidal-wallpaper"
      // Above the shell's static background, beneath normal application windows.
      WlrLayershell.layer: WlrLayer.Bottom
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

      Surface {
        width: parent.width; height: wallpaper.fullHeight
        muted: root.muted ? 1 : 0
        running: !root.paused && !wallpaper.suspended
      }

      // Below screen.y = 0.32, the shader's sand never meets the moving water, foam or shadow.
      // Draw it once in a separate surface so animation does not damage that part of the desktop.
      Variants {
        model: wallpaper.split ? [wallpaper.screen] : []
        PanelWindow {
          required property var modelData
          screen: modelData
          anchors { top: true; left: true; right: true }
          margins.top: wallpaper.movingHeight
          implicitHeight: wallpaper.fullHeight - wallpaper.movingHeight
          color: "#ECECE8"
          exclusionMode: ExclusionMode.Ignore
          mask: Region {}
          WlrLayershell.namespace: "tidal-wallpaper"
          WlrLayershell.layer: WlrLayer.Bottom
          WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

          Surface {
            width: parent.width; height: wallpaper.fullHeight
            y: -wallpaper.movingHeight
            muted: root.muted ? 1 : 0
            running: false
          }
        }
      }
    }
  }
}
