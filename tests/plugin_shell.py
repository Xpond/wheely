"""Exercise the production loader and capability factory across QML model conversion."""
import json
import shutil


def check(repo, base, run, block):
    # Keep the production count handlers, including destruction. Only the compositor's
    # visibility inputs are replaced; QML creates and destroys the objects itself.
    keyboard = (repo / "patches/shell/Ui/KeyboardPanel.qml").read_text()
    keyboard = keyboard.split("  // Count mapped panel surfaces for the shared bar scrim.\n", 1)[1]
    keyboard = keyboard.split("  function beginFocusPrime()", 1)[0]
    clipboard = (repo / "patches/shell/plugins/clipboard/Clipboard.qml").read_text()
    clipboard = clipboard.split("    // Share the bar scrim across panel handoffs.\n", 1)[1]
    clipboard = clipboard.split("    MouseArea {", 1)[0]
    for name, key, code in [("keyboard", "open", '''
      property bool open: false
      property bool centered: true
      property bool backingWindowVisible: true
      property var bar: root.bar
      onOpenChanged: syncSurfaceCount()
''' + keyboard), ("clipboard", "visible", "property bool visible: false\n" + clipboard)]:
        for close_first in (False, True):
            run(f"{name}-destroy-{'closed' if close_first else 'open'}", '''
  property var shell: root
  property var bar: QtObject {
    property int count: 1 // An unrelated panel already owns the backdrop.
    function panelSurfaceVisible(shown) { count += shown ? 1 : -1 }
  }
  property var panel: null
  Component { id: factory; QtObject {
''' + code + '''
  } }
  Component.onCompleted: {
    panel = factory.createObject(root)
    panel.''' + key + ''' = true
    if (bar.count !== 2) throw new Error("FAIL opening did not acquire backdrop")
''' + (f"    panel.{key} = false\n" if close_first else "") + '''
    panel.destroy()
    verify.start()
  }
  Timer {
    id: verify; interval: 1
    onTriggered: {
      if (root.panel !== null || bar.count !== 1)
        throw new Error("FAIL destruction leaked or stole a count: " + bar.count)
      bar.panelSurfaceVisible(false)
      if (bar.count !== 0) throw new Error("FAIL backdrop remained after last panel closed")
      console.log("PASS"); Qt.quit()
    }
  }
''')

    shutil.copyfile(repo / "patches/shell/services/PluginShellApi.qml",
                    base / "PluginShellApi.qml")
    run("plugin-shell-facade", '''
  property int claims: 0
  property int releases: 0
  property var surfaces: []
  QtObject { id: owner }
  PluginShellApi {
    id: api
    pluginId: "xpo.wheel"
    _claimPopout: function(value) { root.claims++; return value === owner }
    _releasePopout: function(value) { if (value === owner) root.releases++ }
    _panelSurfaceVisible: function(shown) { root.surfaces = root.surfaces.concat([shown]) }
  }
  Timer { interval: 1; running: true; onTriggered: {
    api.panelSurfaceVisible(true); api.panelSurfaceVisible(true)
    api.panelSurfaceVisible(false); api.panelSurfaceVisible(false)
    if (!api.claimPopout(owner)) { console.error("FAIL claim"); Qt.exit(1); return }
    api.releasePopout({}); api.releasePopout(owner)
    if (root.claims !== 1 || root.releases !== 1
        || JSON.stringify(root.surfaces) !== "[true,false]") {
      console.error("FAIL callbacks", root.claims, root.releases,
                    JSON.stringify(root.surfaces)); Qt.exit(1)
    } else { console.log("PASS"); Qt.quit() }
  } }
''')

    source = (repo / "patches/shell/shell.qml").read_text()
    methods = ["manifestHasKind", "pluginHasVisualCapabilities", "pluginHasBarCapabilities",
               "pluginShellCapabilityProfile", "createScopedPluginShell", "pluginShellFor",
               "publicPluginManifest", "setPluginSurfaceVisible", "barHasPluginPopouts",
               "isBarWidgetPanelPlugin", "menuPluginMayControl", "summonablePanels"]
    production = "\n".join(block(source, "  function " + name + r"\(") for name in methods)
    production += "\n" + block(source, r"  Instantiator {")
    manifests = {name: json.loads((repo / "plugins" / name / "manifest.json").read_text())
                 for name in ["xpo.wheel", "xpo.files"]}
    widget = {"kinds": ["bar-widget"]}
    manifests["omarchy.weather"] = {**widget, "id": "omarchy.weather", "name": "Weather"}
    manifests["omarchy.dropbox"] = {**widget, "id": "omarchy.dropbox", "name": "Dropbox"}
    manifests["alice.audio"] = {**widget, "id": "alice.audio", "name": "Alice Audio",
                                "omarchy": {"clonedFrom": "omarchy.audio"}}
    manifests["third.radar"] = {"kinds": ["bar-widget", "panel"], "id": "third.radar",
                                "name": "Radar"}
    (base / "Panel.qml").write_text('''import QtQuick
Item {
  property var shell: null
  property var manifest: null
  property bool opened: false
  onOpenedChanged: shell.panelSurfaceVisible(opened)
}
''')

    run("plugin-loader-capabilities", '''
  property var shell: root
  property var _pluginShellApis: ({})
  property var _pluginShellApiDescriptors: ({})
  property var _pluginSurfaceStates: ({})
  property var openPanelIds: ({})
  property var panelLoaders: ({})
  property var panelEntries: ["xpo.wheel", "xpo.files", "third.radar"].map(function(id) {
    return {id: id, manifest: pluginRegistry.installedPlugins[id], kind: "overlay", keepLoaded: true}
  })
  property var pluginRegistry: QtObject {
    property var installedPlugins: ''' + json.dumps(manifests) + '''
    function entryPointUrl(manifest, kind) { return Qt.resolvedUrl("Panel.qml") }
    function resolveEnabledId(id) { return id }
    function isEnabled(id) { return true }
  }
  function isAuthenticationService(manifest, id) { return false }
  property var bar: QtObject {
    property int visiblePanelSurfaces: 0
    function panelSurfaceVisible(shown) { visiblePanelSurfaces += shown ? 1 : -1 }
  }
  property var popoutBar: QtObject {
    property var activePopout: null
    function requestPluginPopout(id, owner) { activePopout = owner }
    function pluginOwnsBarObject(id, owner) { return owner === activePopout }
    function releasePluginPopout(id, owner) {}
    function findPanelWidget(id) { return id === "omarchy.dropbox" ? null : ({}) }
  }
  Component { id: pluginShellApiComponent; PluginShellApi {} }
  function pluginIsIndicatorsClone(manifest) { return false }
  function pluginAppLibraryFor(cacheKey, key) { return {detached: true} }
  function pluginBarStateFor(cacheKey, key) { return null }
  function publicBarConfig() { return ({}) }
  function publicIdleConfigFor(manifest) { return ({}) }
  function registerPanelLoader(id, loader) { panelLoaders[id] = loader }
  function unregisterPanelLoader(id) { delete panelLoaders[id] }
''' + production + '''
  Timer { interval: 100; running: true; onTriggered: {
    function check(condition, message) {
      if (!condition) throw new Error("FAIL " + message)
    }
    var wheel, files
    function listed() {
      return String(wheel.shell.panels().map(function(p) {
        return p.id + ":" + p.name + ":" + p.source }).sort())
    }
    try {
      wheel = root.panelLoaders["xpo.wheel"].item
      files = root.panelLoaders["xpo.files"].item
      check(wheel.shell !== root && files.shell !== root, "plugin received ShellRoot")
      check(wheel.shell.bar !== root.bar && files.shell.bar !== root.bar, "plugin received live bar")
      wheel.opened = true
      check(root.bar.visiblePanelSurfaces === 1, "wheel backdrop missing")
      check(wheel.shell.appLibrary && !files.shell.appLibrary, "menu capability lost or broadened")
      files.opened = true
      wheel.opened = false
      check(root.bar.visiblePanelSurfaces === 1, "handoff dropped Files backdrop")
      files.opened = false
      check(root.bar.visiblePanelSurfaces === 0, "backdrop retained after close")
      var bareBar = root.bar
      check(!wheel.shell.claimPopout(wheel), "claimed a popout the bar cannot own")
      var loaded = "third.radar:Radar:third.radar,xpo.files:Files:xpo.files"
      check(listed() === loaded, "loader panels " + listed())
      root.bar = root.popoutBar
      check(wheel.shell.claimPopout(wheel), "built-in bar refused the popout")
      check(listed() === "alice.audio:Alice Audio:omarchy.audio,omarchy.weather:Weather:omarchy.weather,"
            + loaded, "live panels " + listed())
      check(files.shell.panels().length === 0, "a plugin without menu capability listed panels")
      root.bar = bareBar
      wheel.shell.releasePopout(wheel)
      console.log("PASS"); Qt.quit()
    } catch (error) { console.error(String(error)); Qt.exit(1) }
  } }
''')
