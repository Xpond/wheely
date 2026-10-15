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
const have = keys(manual, "Wheel", "Search", "Files", "Files editor")
assert.ok(rows.some(r => r.keys === "text keys") && rows.some(r => r.keys === "Shift + move keys"), "a rule the exemptions lean on is gone")
for (const [doc, sections] of [["docs/wheel.md", ["Keys"]], ["docs/files.md", ["Keys", "Editing"]]]) {
  const want = keys(read(doc), ...sections)
  assert.ok(want.size > 10, doc + " lost its key table")
  assert.deepEqual([...want].filter(k => !have.has(k) && !RULED.has(k)), [], doc + " lists keys the manual does not")
}

// The sheet keeps every section, in order, in three columns; a combo's keys are drawn one cap each.
const columns = M.manualColumns(rows, 3)
assert.equal(columns.length, 3)
assert.deepEqual(columns.flat().map(c => c.name), [...new Set(rows.filter(r => r.section).map(r => r.section))])
assert.equal(columns.flat().reduce((n, c) => n + c.rows.length, 0), rows.length - 1, "a row fell off the sheet")
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
assert.equal(key("Key_Backspace", 0, "\b").accepted, false, "Backspace did not reach the field")
const calls = []
Object.assign(root, { popOut: () => calls.push("pin"), scrollManual: lines => calls.push(lines) })
for (const [name, mods] of [["Key_Return", 0], ["Key_Down", 0], ["Key_PageUp", 0], ["Key_T", 1 << 26], ["Key_Y", 1 << 26]])
  assert.equal(key(name, mods).accepted, true, name + " acted on the hidden results")
assert.deepEqual(calls, [1, -10, "pin"], "the sheet did not scroll or pin")
key("Key_Escape")
assert.equal(root.reading, false)
assert.equal(root.query, "help rename", "Esc lost the search the sheet was opened from")
console.log("ok: the manual is search rows, covers every documented key, and shows on one sheet")
