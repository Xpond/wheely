.pragma library

// The pinned search's window, shared with Files so a pick from it opens Files inside it.
var window = null

// Also shared with Files: the screen Hyprland has focused, and focusing a window of this shell.
function focusedScreen(monitor, screens) {
  if (!monitor) return null
  for (var i = 0; i < screens.length; i++)
    if (screens[i].name === monitor.name) return screens[i]
  return null
}

function raise(hyprland, title) {
  var all = hyprland.toplevels.values
  for (var i = 0; i < all.length; i++) {
    var t = all[i]
    if (t.wayland && t.wayland.appId === "org.quickshell" && t.title === title)
      hyprland.dispatch("hl.dsp.focus({ window = \"address:0x" + t.address + "\" })")
  }
}
