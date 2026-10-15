// Execute the wheel's queued launch branches without opening desktop targets.
const assert = require("node:assert/strict")
const { method } = require("./qml.js")
const { wheelSource } = require("./wheel-source.js")
const openedSource = wheelSource.match(/^  onOpenedChanged: \{([^]*?)^  }/m)[1]

for (const [entry, expected, returnPanel] of [
  [{ appId: "org.example.Editor", label: "My Editor" }, ["app", "org.example.Editor", "My Editor"]],
  [{ action: "example-command --flag 'two words'" }, ["action", "example-command --flag 'two words'"]],
  [{ id: "trigger.emoji", action: "omarchy-menu-emoji" }, ["action", "omarchy-menu-emoji"], "omarchy.emojis"],
  [{ action: "omarchy-shell shell toggle omarchy.emojis" }, ["action", "omarchy-shell shell toggle omarchy.emojis"], "omarchy.emojis"],
  [{ id: "style.background", action: "background-picker-command" }, ["action", "background-picker-command"], "omarchy.image-picker"],
  [{ id: "trigger.reminder.set", action: "omarchy-reminder -i" }, ["action", "omarchy-reminder -i"], "omarchy.reminders"],
  [{ plugin: "third.notes" }, ["plugin", "third.notes", "{}"]],
  [{ dispatch: "example-dispatch" }, ["window", "example-dispatch"]],
  [{ copy: "42" }, ["copy", "42"]],
  [{ path: "/mnt/My Notes.txt" }, ["exec", ["omarchy-open-path", "/mnt/My Notes.txt"]]],
  [{ address: "0x123" }, ["window", 'hl.dsp.focus({ window = "address:0x123" })']]
]) {
  const effects = [], picks = [], dismissals = [], later = []
  const unmap = { running: false }
  const root = {
    home: "/home/test", opened: true, launched: "", queued: null, slices: [entry], filePending: true, fileAction: "run",
    countUse: e => picks.push(e), dropScan() {},
    dismiss(immediate) { dismissals.push(immediate); unmap.running = !immediate },
    copy: text => effects.push(["copy", text]),
    appLibrary: { launch: (...args) => effects.push(["app", ...args]) },
    shell: { toggle: (...args) => effects.push(["plugin", ...args]), panelSurfaceVisible() {} }
  }
  const Qt = { callLater: fn => later.push(fn) }
  const run = method(wheelSource, "run", { root, unmap,
    Util: { execDetached: command => effects.push(["action", command]) },
    Quickshell: { execDetached: argv => effects.push(["exec", [...argv]]) },
    Hyprland: { dispatch: command => effects.push(["window", command]) } })
  const openedChanged = new Function("root", "Qt", openedSource).bind(null, root, Qt)

  run(null)
  assert.deepEqual([picks, dismissals, effects], [[], [], []], "an empty selection does nothing")
  run(entry)
  assert.equal(root.fileAction, "", "clicking a visible row must replace a pending keyboard action")
  assert.deepEqual(dismissals, [true], "a pick waited for the fade")
  assert.deepEqual(effects, [], "a target ran before the wheel unmapped")
  assert.equal(root.launched, "", "a plugin was recorded before it opened")
  assert.equal(typeof root.queued, "function")
  root.opened = false
  run({ action: "second click after closing" })
  assert.deepEqual(picks, [], "picks re-ranked before the deferred launch")
  openedChanged()
  assert.equal(root.queued, null, "unmapping must consume the queued callback")
  assert.equal(later.length, 1)
  assert.deepEqual(effects, [], "the target ran before the deferred unmap tick")
  openedChanged()
  assert.equal(later.length, 1, "a second close queued the action twice")
  later.shift()()
  assert.deepEqual(picks, [entry], "the deferred launch did not record its pick")
  assert.deepEqual(effects, [expected], "the queued target or its arguments changed")
  assert.equal(root.launched, entry.plugin || returnPanel || "")
}
console.log("ok: picks execute once after unmapping with exact arguments")
