const assert = require("node:assert/strict")
const { read, method, keymap } = require("./qml.js")
const { M, wheelSource } = require("./wheel-source.js")

// The manual is search rows: `help` leads with the whole manual, and a word finds the key for it.
const manual = read("plugins/xpo.wheel/manual.md")
const rows = M.manualRows(manual)
assert.equal(M.search(rows, "help", 40, {})[0].label, "Wheely manual")
assert.equal(M.search(rows, "manual", 40, {})[0].label, "Wheely manual")
for (const [query, trail] of [["rename", "F2 · Files"], ["help trash", "Del · Files"], ["calculator", "= · Search"],
     ["pin search", "Ctrl+T · Search"], ["new folder", "Ctrl+Shift+N · Files"], ["lock preview", "omarchy-shell lock preview · Lock screen"]])
  assert.equal(M.search(rows, query, 40, {})[0]?.trail, trail, query + " misses its row")
assert.ok(rows.every(r => r.manual && !M.keyOf(r) && !M.pinnable(r)), "a manual row is counted or pinned")
assert.ok(rows.every(r => !/[`|]/.test(r.label + r.trail) && r.label !== "What it does"), "markdown leaked into a row")

// Every key the feature docs list is in the manual, but for those its rules cover: "text keys"
// edit the query or the file as any text field does, and "Shift + move keys" scroll the preview.
const RULED = new Set(["Ctrl+Backspace", "Ctrl+A", "Ctrl+K", "Shift+←", "Shift+→", "Shift+Home", "Shift+End",
  "Shift+↑", "Shift+↓", "Shift+PageUp", "Shift+PageDown", "Shift+Space"])
const keys = (md, ...sections) => new Set(sections.flatMap(name =>
  (md.split(/^## /m).find(s => s.startsWith(name + "\n")) || "").split("\n")
    .flatMap(line => line.startsWith("|") ? [...line.split("|")[1].matchAll(/`([^`]+)`/g)].map(m => m[1]) : [])))
assert.ok(rows.some(r => r.keys === "text keys") && rows.some(r => r.keys === "Shift + move keys"), "a rule the exemptions lean on is gone")
// Each doc's keys under the manual's sections for that same feature, not anywhere in the manual;
// the wheel's query editing is Search's "text keys".
for (const [doc, sections, under, ruled] of [
     ["docs/wheel.md", ["Keys"], ["Wheel", "Search"], ["Del", "Ctrl+W", "Home", "End", "Ctrl+U", "Ctrl+V"]],
     ["docs/files.md", ["Keys", "Editing"], ["Files", "Files editor"], []]]) {
  const want = keys(read(doc), ...sections), have = keys(manual, ...under)
  assert.ok(want.size > 10, doc + " lost its key table")
  assert.deepEqual([...want].filter(k => !have.has(k) && !RULED.has(k) && !ruled.includes(k)), [],
    doc + " lists keys the manual's " + under + " does not")
}

// The Files menu: every key its key map takes is in the manual's Files menu, and every key there is taken.
// A key counts with a modifier only when it is not taken bare.
const menuSource = read("plugins/xpo.files/FilesKeys.js").replace(/^\.pragma library/m, "")
const Qt = { ShiftModifier: 1 << 25, ControlModifier: 1 << 26 }
let id = 1
for (const [, k] of menuSource.matchAll(/Qt\.(Key_\w+)/g)) Qt[k] = Qt[k] || id++
const menuKey = new Function("Qt", menuSource + "\nreturn menuKey")(Qt)
const takes = (k, modifiers) => menuKey({ step() {}, fire() {}, back() {}, close() {}, trash() {} }, { key: Qt[k], modifiers })
const CAPS = { Key_Down: "↓", Key_Up: "↑", Key_Backtab: "Shift+Tab", Key_Return: "Enter", Key_Enter: "Enter",
  Key_Right: "→", Key_Left: "←", Key_Escape: "Esc", Key_Delete: "Del" }
const taken = new Set(Object.keys(Qt).filter(k => k.startsWith("Key_")).flatMap(k =>
  takes(k, 0) ? [CAPS[k] || k.slice(4)] : takes(k, Qt.ControlModifier) ? ["Ctrl+" + k.slice(4)]
  : takes(k, Qt.ShiftModifier) ? ["Shift+" + k.slice(4)] : []))
const menuHas = keys(manual, "Files menu")
assert.deepEqual([...taken].filter(k => !menuHas.has(k)), [], "the Files menu takes keys the manual does not list")
assert.deepEqual([...menuHas].filter(k => !taken.has(k)), [], "the manual lists Files menu keys the menu does not take")

// Every fixed menu action without a key of its own is named, word for word, by a Files menu actions row.
const actionRows = rows.filter(r => r.section === "Files menu actions").map(r => (r.keys + " " + r.label).toLowerCase())
const words = text => text.toLowerCase().split(/[^a-z]+/).filter(w => w && !["a", "an", "the", "in", "to", "for", "as"].includes(w))
const actions = [...read("plugins/xpo.files/FilesActions.js").matchAll(/(?:row\("\w+", "([^"]+)", "", function|sub\("\w+", "([^"]+)")/g)]
  .map(m => m[1] || m[2])
assert.ok(actions.length > 15, "the menu's actions were not found")
assert.deepEqual(actions.filter(a => !actionRows.some(r => words(a).every(w => words(r).includes(w)))), [],
  "menu actions the manual does not name")

// The sheet keeps every row, in order, in at most N columns of about equal length. A section carried
// into the next column opens with three rows, and never leaves one behind.
const listed = rows.filter(r => r.section)
const total = listed.length + new Set(listed.map(r => r.section)).size * M.MANUAL_HEAD
for (let count = 1; count <= 4; count++) {
  const columns = M.manualColumns(rows, count), cards = columns.flat()
  assert.ok(columns.length <= count, count + " columns overflowed")
  assert.deepEqual(cards.flatMap(c => c.rows), listed, "a row fell off or moved on the sheet")
  assert.ok(M.manualLength(columns) <= total / count + 3 + M.MANUAL_HEAD, count + " columns are uneven")
  cards.forEach((c, i) => {
    const next = cards[i + 1]
    if (next && next.name === c.name) assert.ok(c.rows.length >= 3 && next.rows.length >= 2, c.name + " splits badly")
  })
}
const combos = keys => M.combosOf(rows.find(r => r.keys === keys)).map(c => c.plain || c.caps.join(" "))
assert.deepEqual(combos("Ctrl+Shift+N"), ["Ctrl Shift N"])
assert.deepEqual(combos("Ctrl+U Ctrl+W"), ["Ctrl U", "Ctrl W"])
assert.deepEqual(combos("wheely settings"), ["wheely settings"])
assert.equal(M.combosOf(rows.find(r => r.keys === "Wheely shortcut"))[0].plain, "Wheely shortcut")

// Enter on any manual row shows the sheet on an empty query. There the field still types, which
// filters rows; keys that would act on the hidden results wait, and Esc gives the query back.
const root = { opened: true, reading: false, query: "help rename", queryAt: 11,
  dismiss() { throw new Error("the manual closed the wheel") } }
root.readManual = method(wheelSource, "readManual", { root })
method(wheelSource, "run", { root, unmap: { running: false }, MenuIndex: M })(rows[3])
assert.equal(root.reading, true)
assert.equal(root.query, "", "the sheet kept the query it was opened from")
root.leaveManual = method(wheelSource, "leaveManual", { root })
const key = keymap("plugins/xpo.wheel/MenuKeys.js", root)
assert.equal(key("Key_A", 0, "a").accepted, false, "typing did not reach the field")
root.query = "a"
assert.equal(key("Key_Backspace", 0, "\b").accepted, false, "Backspace did not reach the field")
const calls = []
Object.assign(root, { popOut: () => calls.push("pin") })
// The sheet always fits, so the arrows and page keys only wait.
for (const [name, mods] of [["Key_Return", 0], ["Key_Down", 0], ["Key_PageUp", 0], ["Key_T", 1 << 26], ["Key_Y", 1 << 26]])
  assert.equal(key(name, mods).accepted, true, name + " acted on the hidden results")
assert.deepEqual(calls, ["pin"], "the sheet did not pin")
key("Key_Escape")
assert.equal(root.reading, false)
assert.equal(root.query, "help rename", "Esc lost the search the sheet was opened from")
console.log("ok: the manual is search rows, covers every documented key, and shows on one sheet")
