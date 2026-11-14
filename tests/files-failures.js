// Review regressions: failed batches, extraction cleanup, hidden targets and probe scope.
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { spawnSync } = require("node:child_process")
const { read, library, method } = require("./qml.js")
const A = library("plugins/xpo.files/FilesActions.js")
const opsSource = read("plugins/xpo.files/FilesOps.qml")
const files = read("plugins/xpo.files/Files.qml")
const base = fs.mkdtempSync(path.join(os.tmpdir(), "files-failures-"))
const at = (...parts) => path.join(base, ...parts)
const run = (argv, env) => spawnSync(argv[0], argv.slice(1), { encoding: "utf8", env })
try {
  fs.mkdirSync(at("dest"))
  const root = { panel: { listedDir: at("dest") }, note(text) { this.message = text } }
  const exited = new Function("root", "gauge", "totaller", "exitCode", opsSource.match(/onExited: function \(exitCode\) \{([\s\S]*?)\n    \}/)[1])
  for (const name of ["pasteCommand", "paste"]) root[name] = method(opsSource, name, { root })
  root.run = (command, about) => { root.op = about; root.status = run(command).status; exited(root, {}, { cancel() {} }, root.status) }
  const hold = (names, move = true) => ({ items: names.map(name => ({ name, path: at(name) })), move, name: names.length + " items" })

  // Nothing moved: preserve the hold so the failure can be corrected and retried.
  root.held = hold(["missing.txt"])
  root.paste()
  assert.equal(root.status, 1)
  assert.ok(root.held)
  // Some moved and some failed: clear stale paths, regardless of which one failed first.
  for (const names of [["ok-a.txt", "missing.txt"], ["missing.txt", "ok-b.txt"]]) {
    const good = names.find(n => n !== "missing.txt")
    fs.writeFileSync(at(good), "move me")
    root.held = hold(names)
    root.paste()
    assert.equal(root.status, 19)
    assert.equal(root.held, null)
    assert.equal(root.message, "some items moved; others could not be moved")
    assert.equal(fs.readFileSync(at("dest", good), "utf8"), "move me")
  }
  // A cancelled move keeps the hold, and pasting it again goes on past what already moved.
  fs.writeFileSync(at("dest", "went.txt"), "moved"); fs.writeFileSync(at("left.txt"), "move me")
  root.held = hold(["went.txt", "left.txt"])
  root.op = { doing: "moving 2 items", spend: true }; root.cancelling = true
  exited(root, {}, { cancel() {} }, 130)
  root.cancelling = false
  assert.equal(root.message, "2 items cancelled")
  root.paste()
  assert.equal(root.status, 18)
  assert.equal(fs.readFileSync(at("dest", "left.txt"), "utf8"), "move me")
  // Copy failure uses the same status, but copied sources stay valid for another paste.
  fs.writeFileSync(at("copy.txt"), "copy me")
  root.held = hold(["copy.txt", "missing.txt"], false)
  root.paste()
  assert.equal(root.status, 19)
  assert.ok(root.held)
  assert.equal(root.message, "some items copied; others could not be copied")
  for (const name of ["a.txt", "b.txt"]) {
    fs.writeFileSync(at(name), "source")
    fs.writeFileSync(at("dest", name), "keep")
  }
  root.held = hold(["a.txt", "b.txt"])
  root.paste()
  assert.equal(root.status, 17)
  assert.ok(root.held)
  assert.equal(root.message, "all 2 names are already here")
  // A copy that lands lets go too, so the legend stops offering it; a hold taken mid-paste stays.
  fs.writeFileSync(at("whole.txt"), "copy me")
  root.held = hold(["whole.txt"], false)
  root.paste()
  assert.equal(root.status, 0)
  assert.equal(root.held, null, "a pasted copy stayed held")
  const later = hold(["later.txt"], false)
  root.op = { spend: hold(["whole.txt"], false) }; root.held = later
  exited(root, {}, { cancel() {} }, 0)
  assert.equal(root.held, later, "a paste dropped a hold taken while it ran")
  console.log("ok: partial moves clear stale holds, total failures retain them, and collisions report the whole batch")

  // Real extraction, with only its final rename forced to fail. Both archive layouts clean up.
  fs.mkdirSync(at("bin")); fs.mkdirSync(at("input")); fs.mkdirSync(at("input", "wrapped"))
  fs.writeFileSync(at("bin", "mv"), "#!/bin/sh\nexit 1\n", { mode: 0o755 })
  fs.writeFileSync(at("input", "file.txt"), "payload")
  fs.writeFileSync(at("input", "wrapped", "file.txt"), "payload")
  for (const name of ["loose", "wrapped"]) {
    const archive = at(name + ".tar"), out = at(name + "-out")
    fs.mkdirSync(out)
    assert.equal(run(["bsdtar", "-cf", archive, "-C", at("input"), name === "loose" ? "file.txt" : "wrapped"]).status, 0)
    assert.equal(run(A.extractCommand(archive, path.join(out, name)), { ...process.env, PATH: at("bin") + ":" + process.env.PATH }).status, 1)
    assert.deepEqual(fs.readdirSync(out), [], "a failed final rename left extraction files")
  }
  console.log("ok: both extraction layouts remove scratch files when their final rename fails")

  // Record real probe dispatch without querying this machine's applications or tailnet.
  fs.writeFileSync(at("bin", "gio"), '#!/bin/sh\necho "gio $1" >> "$PROBE_LOG"\n[ "$1" != info ] || echo "  standard::content-type: text/plain"\n', { mode: 0o755 })
  fs.writeFileSync(at("bin", "tailscale"), '#!/bin/sh\necho tailscale >> "$PROBE_LOG"\n', { mode: 0o755 })
  const file = { path: at("a.txt"), isDir: false }, folder = { path: at("input"), isDir: true }
  for (const [entry, targets, expected] of [[file, [file], ["gio info", "gio mime", "tailscale"]],
    [folder, [folder], ["gio info", "gio mime"]], [null, [file, file], ["tailscale"]],
    [null, [file, folder], []], [null, [], []], [{ ...file, missing: true }, [{ ...file, missing: true }], []]]) {
    fs.writeFileSync(at("probe.log"), "")
    const command = A.probeCommand(entry, targets)
    if (command.length) assert.equal(run(command, { ...process.env, PATH: at("bin") + ":" + process.env.PATH, PROBE_LOG: at("probe.log") }).status, 0)
    assert.deepEqual(fs.readFileSync(at("probe.log"), "utf8").trim().split("\n").filter(Boolean), expected)
  }
  console.log("ok: probes query MIME apps only for one entry and Taildrop only for files")
} finally {
  fs.rmSync(base, { recursive: true, force: true })
}

const entries = Array.from({ length: 5 }, (_, i) => ({ name: "f" + i, path: "/d/f" + i }))
const panel = { listedEntries: entries, rows: entries.slice(0, 2), marked: Object.fromEntries(entries.map(e => [e.path, true])) }
const marks = new Function("root", "return " + files.match(/readonly property var marks: (.*)/)[1])
panel.marks = marks(panel)
panel.hiddenMarks = new Function("root", files.match(/readonly property int hiddenMarks: \{([\s\S]*?)\n  \}/)[1])(panel)
assert.equal(panel.hiddenMarks, 3)
const root = { panel, doomed: entries.map(e => e.path).join("\n") }
const doomedName = new Function("root", opsSource.match(/readonly property string doomedName: \{([\s\S]*?)\n  \}/)[1])
assert.equal(doomedName(root), "5 items (3 hidden)")
root.doomed = "/d/unmarked"
assert.equal(doomedName(root), "unmarked", "an unmarked entry inherited another selection's hidden count")
const rows = A.tree({ panel, ops: { label: method(opsSource, "label", {}) }, many: entries, hidden: panel.hiddenMarks,
  dir: "/d", peers: [], urls: [], held: null, doomed: true })
assert.equal(rows.find(r => r.id === "count").label, "5 items (3 hidden)")
assert.equal(rows.find(r => r.id === "trash").label, "Again to trash 5 items (3 hidden)")
panel.listedEntries = entries.map((e, i) => i === 0 ? { ...e, missing: true } : e)
assert.equal(marks(panel).length, 4, "a Git-deleted row stayed marked")
console.log("ok: hidden targets appear in both trash prompts, and missing entries leave the marks")
