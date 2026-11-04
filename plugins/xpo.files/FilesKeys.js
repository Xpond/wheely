.pragma library

// A modifier pressed on its own waits for the key it modifies.
var MODIFIERS = [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_AltGr, Qt.Key_Meta, Qt.Key_Super_L, Qt.Key_Super_R]

// The menu's own keys; false for any other, which closes it and then does what it always does.
function menuKey(menu, event) {
  var ctrl = (event.modifiers & Qt.ControlModifier) && !(event.modifiers & Qt.ShiftModifier)
  switch (event.key) {
  case Qt.Key_Down: case Qt.Key_Tab:   menu.step(1); return true
  case Qt.Key_Up:   case Qt.Key_Backtab: menu.step(-1); return true
  case Qt.Key_Home: menu.step(-Infinity); return true
  case Qt.Key_End:  menu.step(Infinity); return true
  case Qt.Key_N: if (ctrl) menu.step(1); return !!ctrl
  case Qt.Key_P: if (ctrl) menu.step(-1); return !!ctrl
  case Qt.Key_Return: case Qt.Key_Enter: menu.fire(); return true
  case Qt.Key_Right: menu.fire(null, true); return true
  case Qt.Key_Left: case Qt.Key_Backspace: menu.back(); return true
  case Qt.Key_Escape: case Qt.Key_Menu: menu.close(); return true
  case Qt.Key_F10: if (event.modifiers & Qt.ShiftModifier) menu.close(); return !!(event.modifiers & Qt.ShiftModifier)
  // Read before confirming, which disarms it: a Del that trashed must not go on to arm the next row.
  case Qt.Key_Delete: var armed = menu.armed; if (armed) menu.confirm(); return armed
  }
  return false
}

// Keep the key map pure enough to exercise without a running shell.
function onKey(panel, ops, preview, event) {
  if (panel.editing) {
    if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_S) { panel.save(); event.accepted = true; return }
    if (event.key === Qt.Key_Escape) { panel.leaveEdit(); event.accepted = true }
    return
  }
  var menu = panel.menu
  if (menu && menu.open) {
    if (MODIFIERS.indexOf(event.key) >= 0) return
    // An armed Trash survives only its confirming key: Del, or Enter on the Trash row.
    var enter = event.key === Qt.Key_Return || event.key === Qt.Key_Enter
    if (ops.doomed && event.key !== Qt.Key_Delete && !(enter && menu.current === "trash")) ops.doomed = ""
    if (menuKey(menu, event)) { event.accepted = true; return }
    menu.close()
  }
  // Any key except the confirming Delete disarms deletion.
  if (ops.doomed && event.key !== Qt.Key_Delete) ops.doomed = ""

  if (panel.naming) {
    switch (event.key) {
    case Qt.Key_Escape: panel.naming = ""; break
    case Qt.Key_Return:
    case Qt.Key_Enter:  panel.commitName(); break
    default: panel.renameKey(event)
    }
    // Keep every key from moving the selection during naming.
    event.accepted = true
    return
  }
  if (menu && (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier)))) {
    menu.openHere(); event.accepted = true; return
  }
  if (event.key === Qt.Key_Space && panel.showsVideo && !event.modifiers) {
    if (!event.isAutoRepeat) preview.toggleVideo()
    event.accepted = true
    return
  }
  if (event.modifiers & Qt.ControlModifier) {
    switch (event.key) {
    case Qt.Key_E: panel.edit(); event.accepted = true; return
    // The marks when there are any, the selection otherwise.
    case Qt.Key_C: ops.hold(panel.targets, false); event.accepted = true; return
    case Qt.Key_X: ops.hold(panel.targets, true); event.accepted = true; return
    case Qt.Key_V: ops.paste(); event.accepted = true; return
    case Qt.Key_H: panel.showHidden = !panel.showHidden; event.accepted = true; return
    case Qt.Key_U: panel.filter = ""; event.accepted = true; return
    case Qt.Key_Y: ops.copyPath(panel.targets); event.accepted = true; return
    case Qt.Key_Space: panel.toggleMark(); event.accepted = true; return
    case Qt.Key_A: panel.markAll(); event.accepted = true; return
    case Qt.Key_Return:
    case Qt.Key_Enter: ops.terminal(); event.accepted = true; return
    case Qt.Key_O: panel.cycleOrder(); event.accepted = true; return
    case Qt.Key_T: panel.popOut(); event.accepted = true; return
    case Qt.Key_B: panel.listShown = !panel.listShown; event.accepted = true; return
    case Qt.Key_D: panel.diffMode = !panel.diffMode; event.accepted = true; return
    case Qt.Key_N:
      if (event.modifiers & Qt.ShiftModifier) panel.beginNew()
      else panel.move(1)
      event.accepted = true; return
    case Qt.Key_P: panel.move(-1); event.accepted = true; return
    case Qt.Key_W:
    case Qt.Key_Backspace:
      panel.filter = panel.pathMode
        ? (panel.filter.replace(/\/+$/, "").replace(/[^\/]*$/, "") || panel.filter.charAt(0))
        : panel.filter.replace(/\S+\s*$/, "")
      event.accepted = true; return
    }
  }
  // With the list hidden the preview is the view: bare keys scroll it, and the keys that
  // would go up (←, Backspace with nothing to delete) bring the list back instead.
  var reading = !panel.listShown && !(event.modifiers & (Qt.ControlModifier | Qt.ShiftModifier))
  if (reading && (event.key === Qt.Key_Left || (event.key === Qt.Key_Backspace && !panel.filter))) {
    panel.listShown = true; event.accepted = true; return
  }
  // Shift directs navigation to the preview pane.
  if ((event.modifiers & Qt.ShiftModifier) || reading) {
    switch (event.key) {
    case Qt.Key_Down:  preview.scrollBy(panel.lineHeight * 3); event.accepted = true; return
    case Qt.Key_Up:    preview.scrollBy(-panel.lineHeight * 3); event.accepted = true; return
    case Qt.Key_Right: preview.scrollAcross(preview.panStep); event.accepted = true; return
    case Qt.Key_Left:  preview.scrollAcross(-preview.panStep); event.accepted = true; return
    case Qt.Key_PageDown: preview.scrollBy(preview.pageStep); event.accepted = true; return
    case Qt.Key_PageUp:   preview.scrollBy(-preview.pageStep); event.accepted = true; return
    case Qt.Key_Home:  preview.scrollTo(0); event.accepted = true; return
    case Qt.Key_End:   preview.scrollTo(1); event.accepted = true; return
    }
  }
  switch (event.key) {
  case Qt.Key_Escape:
    if (panel.marks && panel.marks.length) panel.unmarkAll()
    else if (panel.filter) panel.filter = ""
    else if (panel.host) panel.toWheel()
    else panel.close()
    event.accepted = true; return
  case Qt.Key_Backspace:
    if (panel.filter) panel.filter = panel.filter.slice(0, -1)
    else if (panel.dir !== panel.home) panel.up()
    else panel.toWheel()
    event.accepted = true; return
  case Qt.Key_Left:  panel.up(); event.accepted = true; return
  case Qt.Key_Down:  panel.move(1); event.accepted = true; return
  case Qt.Key_Up:    panel.move(-1); event.accepted = true; return
  case Qt.Key_Tab:   panel.move(1); event.accepted = true; return
  case Qt.Key_Backtab: panel.move(-1); event.accepted = true; return
  case Qt.Key_PageDown: panel.goTo(panel.index + panel.listPage); event.accepted = true; return
  case Qt.Key_PageUp:   panel.goTo(panel.index - panel.listPage); event.accepted = true; return
  case Qt.Key_Home:  panel.goTo(0); event.accepted = true; return
  case Qt.Key_End:   panel.goTo(panel.rows.length - 1); event.accepted = true; return
  case Qt.Key_F1:    panel.allKeys = !panel.allKeys; event.accepted = true; return
  case Qt.Key_F2:    panel.beginRename(); event.accepted = true; return
  case Qt.Key_Delete: ops.remove(panel.targets); event.accepted = true; return
  // Only Enter opens a file; → just steps into folders.
  case Qt.Key_Right:
    if (panel.sel && panel.sel.isDir) ops.activate(panel.sel)
    event.accepted = true; return
  case Qt.Key_Return:
  case Qt.Key_Enter:
    ops.activate(panel.sel); event.accepted = true; return
  }
  if (event.text && event.text.length === 1 && event.text >= " ") {
    // A leading / starts the path from the folder being browsed, or from home outside it.
    if (!panel.filter && event.text === "/")
      panel.filter = (panel.dir + "/").indexOf(panel.home + "/") === 0 ? panel.dir.slice(panel.home.length) + "/" : "/"
    else panel.filter += event.text
    panel.index = 0
    panel.pending = ""
    event.accepted = true
  }
}
