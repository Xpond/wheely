// The right-click menu: what each kind of entry is offered, the menu's keys, and its commands run
// for real against disposable files.
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { spawnSync } = require("node:child_process")
const { read, library, method, keymap } = require("./qml.js")
const A = library("plugins/xpo.files/FilesActions.js")
const panelSource = read("plugins/xpo.files/Files.qml")
const opsSource = read("plugins/xpo.files/FilesOps.qml")

// Rows as a string: ids in order, | for a separator, a submenu's rows in brackets.
const ids = rows => rows.map(r => r.sep ? "|" : r.id + (r.sub ? "[" + ids(r.sub) + "]" : "")).join(" ")
const find = (rows, id) => rows.find(r => r.id === id)
const calls = []
const ops = {
  doomed: "", label: method(opsSource, "label", {}), activate: e => calls.push(["open", e.name]), copyPath: () => calls.push(["path"]),
  launch: argv => calls.push(["launch", ...argv]), terminal: dir => calls.push(["terminal", dir]),
  detach: argv => calls.push(["detach", ...argv]), run: (argv, about) => calls.push(["run", argv, about]),
  hold: (e, move) => calls.push(["hold", [].concat(e).map(x => x.name).join(), move]), paste: into => calls.push(["paste", into]),
  remove() { this.doomed = this.doomed ? "" : "armed"; calls.push(["remove"]) }
}
const panel = { edit: () => calls.push(["edit"]), beginRename: e => calls.push(["rename", e.name]),
  beginCopyName: (verb, e) => calls.push(["name", verb, e.name]), beginNew: () => calls.push(["new"]), popOut: () => calls.push(["pop"]) }
const file = (name, extra) => Object.assign({ name, path: "/home/t/d/" + name, isDir: false, size: 1 }, extra)
const menu = (entry, extra) => A.tree(Object.assign({ panel, ops, entry, many: null, dir: "/home/t/d", held: null, image: false,
  video: false, urls: ["file:///home/t/d/x"], editable: false, script: false, executable: false, apps: [], preferred: "",
  peers: [], doomed: false, showHidden: false, order: "name", popped: false }, extra))

// What each kind of entry is offered.
const apps = [{ id: "imv", name: "imv" }, { id: "nvim", name: "Neovim", terminal: true, command: ["nvim"] }]
const image = menu(file("photo.jpg"), { image: true, apps, preferred: "imv", peers: ["laptop"] })
assert.equal(ids(image), "open with[with:imv with:nvim] nautilus | share[localsend to:laptop clip pixels] "
  + "convert[as:jpg-high as:jpg-medium as:jpg-low as:png-high as:png-medium as:png-low] wallpaper "
  + "compress[pack.zip pack.tar.zst] | cut copy duplicate rename link | path trash | here[new terminal nautilus | hidden by:name by:date by:size window]")
assert.equal(find(image, "with").sub[0].hint, "default", "the default app is not marked")
assert.equal(ids(find(menu(file("clip.mkv"), { video: true }), "convert").sub), "as:mp4-4k as:mp4-1080p as:mp4-720p as:gif-4k as:gif-1080p as:gif-720p")
assert.ok(!find(find(menu(file("clip.mkv"), { video: true }), "share").sub, "pixels"), "a video offers Copy image")
for (const [name, stem] of [["src.tar.gz", "src"], ["Pack.ZIP", "Pack"], ["notes.gz", ""], [".zip", ""], ["disk.iso", "disk"]])
  assert.equal(A.archiveStem(name), stem, name)
assert.ok(find(menu(file("src.tar.gz")), "extract") && !find(image, "extract"))
// Run only once it can: a script not executable would only fail with 126.
const script = menu(file("go.sh"), { script: true }), runnable = menu(file("go.sh"), { script: true, executable: true })
assert.ok(find(script, "exec") && !find(script, "run"), "a script that cannot run offers Run, or not Make executable")
assert.ok(find(runnable, "run") && !find(runnable, "exec"), "an executable script offers Make executable, or not Run")
assert.ok(A.isScript("tool", "#!/bin/sh\n") && A.isScript("x.py", "") && !A.isScript("x.txt", "plain"))
assert.ok(find(menu(file("a.txt"), { editable: true }), "edit") && !find(image, "edit"))
const folder = menu(file("docs", { isDir: true }))
assert.ok(find(folder, "terminal") && find(folder, "compress") && !find(folder, "convert"))
assert.equal(ids(find(folder, "share").sub), "localsend clip", "a folder can go by Taildrop")
assert.equal(ids(menu(file("gone.txt", { missing: true }))), "open path", "a deleted row offers more than its diff and path")
// A preview's deleted child must become the selection before its diff can be shown.
const deleted = file("gone.txt", { path: "/home/t/d/sub/gone.txt", missing: true })
const browsing = { sel: file("sub", { isDir: true }), listedDir: "/home/t/d", diffMode: false,
  rows: [], index: 0, pending: "", enter(dir) { this.listedDir = dir; this.rows = []; this.index = 0 } }
browsing.claimPending = method(panelSource, "claimPending", { root: browsing, Qt: { callLater() {} } })
const opening = { panel: browsing }
opening.activate = method(opsSource, "activate", { root: opening })
find(menu(deleted, { panel: browsing, ops: opening }), "open").run()
assert.deepEqual([browsing.listedDir, browsing.pending, browsing.diffMode], ["/home/t/d/sub", "gone.txt", true])
browsing.rows = [file("another.txt"), deleted]; browsing.claimPending()
assert.equal(browsing.rows[browsing.index].path, deleted.path, "Show changes did not land on the deleted child")
const root = ids(menu(file("/mnt", { path: "/mnt", isDir: true, shortcut: true })))
for (const id of ["cut", "copy", "rename", "duplicate", "link", "trash", "compress"])
  assert.ok(!root.split(/[ \[\]]/).includes(id), "a root's row offers " + id)
assert.equal(ids(menu(file("a.txt"), { apps: null })).split(" ")[1], "with[looking]")
assert.ok(find(menu(file("a.txt"), { apps: null }), "with").sub[0].off, "the wait for apps can be chosen")
assert.equal(ids(menu(null)), "new terminal nautilus | hidden by:name by:date by:size window")
for (const rows of [image, folder, script, menu(null), menu(file("x"), { apps: [] })]) {
  const s = ids(rows)
  assert.ok(!/^\||\|$|\| \||\[\||\|\]/.test(s), "a stray separator in " + s)
  // Beside a menu that is itself beside another there is no room left, so none opens two deep.
  assert.ok(!rows.some(r => r.sub && r.sub.some(t => t.sub)), "a submenu holds a submenu in " + s)
}
assert.equal(find(find(image, "share").sub, "to:laptop").label, "Taildrop to laptop")

// Holding something offers it here, and into a folder row unless the row is what is held.
const held = { items: [{ path: "/home/t/x/a.txt", name: "a.txt" }], name: "a.txt", move: true }
const into = menu(file("docs", { isDir: true }), { held })
assert.equal(find(into, "into").label, "Move a.txt into docs")
assert.equal(find(into, "paste").label, "Move a.txt here")
assert.ok(!find(menu(file("a.txt", { path: held.items[0].path, isDir: true }), { held }), "into"), "a folder offered into itself")
assert.equal(find(menu(null, { held: { ...held, move: false } }), "paste").label, "Copy a.txt here")

// The rows run what they say. Trash asks twice and stays open in between.
calls.length = 0
find(image, "open").run(); find(image, "rename").run(); find(image, "duplicate").run(); find(image, "link").run()
find(find(image, "with").sub, "with:imv").run(); find(find(image, "with").sub, "with:nvim").run()
find(find(image, "share").sub, "to:laptop").run()
find(menu(null), "by:date").run()
assert.equal(panel.order, "date", "Sort did not set the order")
assert.deepEqual(calls.slice(0, 7), [["open", "photo.jpg"], ["rename", "photo.jpg"], ["name", "copy", "photo.jpg"], ["name", "link", "photo.jpg"],
  ["launch", "uwsm-app", "--", "gtk-launch", "imv.desktop", "/home/t/d/photo.jpg"],
  ["launch", "omarchy-launch-tui", "nvim", "/home/t/d/photo.jpg"],
  ["detach", "omarchy-tailscale-send", "laptop", "/home/t/d/photo.jpg"]])
ops.doomed = ""
assert.equal(find(image, "trash").run(), true, "the first Trash closed the menu")
assert.equal(find(menu(file("photo.jpg"), { doomed: true }), "trash").label, "Again to trash photo.jpg")
assert.equal(find(image, "trash").run(), false, "the second Trash kept the menu open")
// An entry of a folder's preview is not in the folder listed: Extract and Compress write beside it.
const inner = menu(file("src.tar.gz", { path: "/home/t/d/sub/src.tar.gz" }))
calls.length = 0
find(inner, "extract").run(); find(find(inner, "compress").sub, "pack.zip").run()
assert.deepEqual(calls.map(c => c[1]), [A.extractCommand("/home/t/d/sub/src.tar.gz", "/home/t/d/sub/src"),
  A.compressCommand("/home/t/d/sub", "/home/t/d/sub/src.tar.gz.zip", ["src.tar.gz"])], "a preview's entry wrote into the folder listed")
assert.ok(calls.every(c => !c[2].land), "a preview's archive operation requested landing in its parent listing")
for (const dir of ["/home/t/d", "/home/t/d/"]) {
  const here = menu(file("src.tar.gz"), { dir })
  calls.length = 0
  find(here, "extract").run(); find(find(here, "compress").sub, "pack.zip").run()
  assert.ok(calls.every(c => c[2].land), "an archive operation in the listed folder did not request landing")
}
console.log("ok: the menu offers each kind of entry its own rows, and each row runs its verb")

// Marks get the verbs that take many; Taildrop only while every mark is a file.
const marks = [file("a.jpg"), file("b.jpg"), file("docs", { isDir: true })]
const many = menu(null, { many: marks, peers: ["laptop"], urls: marks.map(e => "file://" + e.path) })
assert.equal(ids(many), "count | share[localsend clip] compress[pack.zip pack.tar.zst] | cut copy unmark | path trash "
  + "| here[new terminal nautilus | hidden by:name by:date by:size window]")
assert.deepEqual([find(many, "count").label, find(many, "count").off, find(many, "trash").label], ["3 items", true, "Trash 3 items"])
assert.equal(find(find(many, "compress").sub, "pack.zip").label, "d.zip", "many are not archived after their folder")
assert.equal(find(find(menu(null, { many: marks, dir: "/home/t/d/" }), "compress").sub, "pack.zip").label, "d.zip",
  "a typed path's trailing slash named the archive .zip")
const photos = menu(null, { many: marks.slice(0, 2), peers: ["laptop"], urls: ["file:///a", "file:///b"] })
calls.length = 0
for (const id of ["localsend", "clip"]) find(find(photos, "share").sub, id).run()
find(find(photos, "share").sub, "to:laptop").run()
find(find(photos, "compress").sub, "pack.zip").run()
find(photos, "cut").run(); find(photos, "path").run()
assert.deepEqual(calls.map(c => c[0] === "run" ? c[1] : c), [
  ["launch", "omarchy-menu-share", "file", "/home/t/d/a.jpg", "/home/t/d/b.jpg"],
  A.clipCommand(["file:///a", "file:///b"]),
  ["detach", "omarchy-tailscale-send", "laptop", "/home/t/d/a.jpg", "/home/t/d/b.jpg"],
  A.compressCommand("/home/t/d", "/home/t/d/d.zip", ["a.jpg", "b.jpg"]),
  ["hold", "a.jpg,b.jpg", true], ["path"]])
console.log("ok: marks get one menu of the verbs that take many")

// The probe's answer: the default app first, only online Taildrop targets.
const probe = A.readProbe('executable\nDefault application for “text/plain”: nvim.desktop\nRegistered applications:\n'
  + '\tnvim.desktop\n\tomawrite.desktop\nRecommended applications:\n\tomawrite.desktop\n\tnvim.desktop\npeers\n'
  + '100.1.1.1\tlaptop\n100.1.1.2\tphone\toffline; last seen 3h ago\n')
assert.deepEqual(probe, { executable: true, apps: ["nvim", "omawrite"], preferred: "nvim", peers: ["laptop"] })
assert.deepEqual(A.readProbe("peers\n"), { executable: false, apps: [], preferred: "", peers: [] })

// The menu's keys while it is open; any other key closes it and does what it always does.
const seen = []
const open = { open: false, current: "", trashes: true,
  step: d => seen.push("step " + d), fire: (row, into) => seen.push(into ? "into" : "fire"), back: () => seen.push("back"),
  close() { this.open = false; seen.push("close") }, trash() { seen.push("trash"); return this.trashes },
  openHere() { this.open = true; seen.push("open") } }
const doom = { doomed: "", remove: () => seen.push("remove") }
const browser = { menu: open, editing: false, naming: "", listShown: true, filter: "",
  beginRename: () => seen.push("rename"), beginNew: () => seen.push("new"), renameKey: () => seen.push("typed") }
const CTRL = 1 << 26, SHIFT = 1 << 25
const key = keymap("plugins/xpo.files/FilesKeys.js", browser, doom, {})
const press = (k, m) => { seen.length = 0; key(k, m); return seen.join() }
assert.equal(press("Key_Menu"), "open")
for (const [k, m, want] of [["Key_Down", 0, "step 1"], ["Key_Tab", 0, "step 1"], ["Key_Backtab", SHIFT, "step -1"],
    ["Key_N", CTRL, "step 1"], ["Key_P", CTRL, "step -1"], ["Key_Home", 0, "step -Infinity"], ["Key_Return", 0, "fire"],
    ["Key_Right", 0, "into"], ["Key_Left", 0, "back"], ["Key_Backspace", 0, "back"], ["Key_Shift", SHIFT, ""]])
  assert.equal(press(k, m), want, k)
assert.equal(press("Key_F2"), "close,rename", "F2 did not close the menu and rename")
assert.equal(press("Key_F10", SHIFT), "open")
assert.equal(press("Key_F10", SHIFT), "close", "Shift+F10 does not close the menu it opened")
open.open = true
assert.equal(press("Key_N", CTRL | SHIFT), "close,new", "Ctrl+Shift+N stepped the menu")
// Del belongs to the menu even when it has no Trash action.
open.open = true
assert.equal(press("Key_Delete"), "trash", "Del in the menu did more than its Trash")
open.trashes = false
assert.equal(press("Key_Delete"), "trash", "Del escaped a menu without Trash")
assert.equal(open.open, true, "Del dismissed a menu without Trash")
open.open = true; doom.doomed = "/x"; open.current = "trash"; key("Key_Return")
assert.equal(doom.doomed, "/x", "Enter on the armed Trash disarmed it")
open.open = true; doom.doomed = "/x"; key("Key_Down")
assert.equal(doom.doomed, "", "moving off an armed Trash left it armed")
open.open = false; browser.naming = "rename"
assert.equal(press("Key_Menu"), "typed", "the menu opened over a name being typed")
browser.naming = ""; browser.editing = true
assert.equal(press("Key_Menu"), "", "the menu opened over an edit")
console.log("ok: the menu's keys move, run, go back and close; other keys close it and do their own")

// Ctrl+M marks and Ctrl+A marks all; the verbs take the marks, and Esc lets them go first.
browser.editing = false; browser.filter = "typed"
Object.assign(browser, { marks: [{ path: "/m" }], targets: ["the targets"], toggleMark: () => seen.push("mark"),
  markAll: () => seen.push("all"), unmarkAll() { this.marks = []; seen.push("unmark") } })
Object.assign(doom, { hold: (list, move) => seen.push("hold " + list + " " + move), copyPath: list => seen.push("path " + list),
  remove: list => seen.push("remove " + list) })
for (const [k, m, want] of [["Key_M", CTRL, "mark"], ["Key_A", CTRL, "all"], ["Key_C", CTRL, "hold the targets false"],
    ["Key_X", CTRL, "hold the targets true"], ["Key_Y", CTRL, "path the targets"], ["Key_Delete", 0, "remove the targets"],
    ["Key_Escape", 0, "unmark"]])
  assert.equal(press(k, m), want, k)
press("Key_Escape")
assert.equal(browser.filter, "", "Esc with no marks left did not clear the field")
console.log("ok: ctrl+m and ctrl+a mark, the verbs take the marks, and esc lets them go before the field")

// Duplicate and Make link start from the name with a word before its extension.
for (const [name, isDir, verb, want, caret] of [["photo.jpg", false, "copy", "photo copy.jpg", "photo copy"],
    ["v1.2", true, "link", "v1.2 link", "v1.2 link"], [".bashrc", false, "copy", ".bashrc copy", ".bashrc copy"]]) {
  const p = { sel: { name, isDir }, editing: false }
  method(panelSource, "beginCopyName", { root: p })(verb)
  assert.deepEqual([p.naming, p.renameTo, p.renameTo.slice(0, p.renameAt)], [verb, want, caret], name)
}

// The commands themselves, on disposable files: nothing is overwritten, and a failure leaves nothing.
const base = fs.mkdtempSync(path.join(os.tmpdir(), "files-menu-"))
try {
  const sh = argv => spawnSync(argv[0], argv.slice(1), { encoding: "utf8" })
  const at = (...p) => path.join(base, ...p)
  const tree = dir => spawnSync("find", [dir, "-mindepth", "1"], { encoding: "utf8" }).stdout.split("\n").filter(Boolean)
    .map(p => path.relative(dir, p)).sort()
  fs.mkdirSync(at("-odd dir/sub"), { recursive: true })
  fs.writeFileSync(at("-odd dir/a.txt"), "a"); fs.writeFileSync(at("-odd dir/sub/b.txt"), "b")
  for (const ext of [".zip", ".tar.zst"]) {
    assert.equal(sh(A.compressCommand(base, at("-odd dir" + ext), ["-odd dir"])).status, 0, ext)
    const listed = sh(["bsdtar", "-tf", at("-odd dir" + ext)]).stdout.split("\n").filter(Boolean).map(s => s.replace(/\/$/, ""))
    assert.deepEqual(listed.sort(), ["-odd dir", "-odd dir/a.txt", "-odd dir/sub", "-odd dir/sub/b.txt"], ext + " holds the path")
    const before = fs.readFileSync(at("-odd dir" + ext))
    assert.equal(sh(A.compressCommand(base, at("-odd dir" + ext), ["-odd dir"])).status, 17, ext + " overwrote an archive")
    assert.deepEqual(fs.readFileSync(at("-odd dir" + ext)), before)
  }
  // Many go into one archive, by name.
  assert.equal(sh(A.compressCommand(at("-odd dir"), at("-odd dir", "both.zip"), ["a.txt", "sub"])).status, 0)
  assert.deepEqual(sh(["bsdtar", "-tf", at("-odd dir", "both.zip")]).stdout.split("\n").filter(Boolean).sort(), ["a.txt", "sub/", "sub/b.txt"])
  fs.unlinkSync(at("-odd dir", "both.zip"))
  fs.mkdirSync(at("out"))
  // An archive of one folder named as it is unwraps; loose files go into a folder named after it.
  fs.renameSync(at("-odd dir.zip"), at("out", "-odd dir.zip"))
  assert.equal(sh(A.extractCommand(at("out", "-odd dir.zip"), at("out", "-odd dir"))).status, 0)
  assert.deepEqual(tree(at("out", "-odd dir")), ["a.txt", "sub", "sub/b.txt"])
  assert.equal(sh(A.extractCommand(at("out", "-odd dir.zip"), at("out", "-odd dir"))).status, 17, "an extract overwrote its folder")
  assert.equal(sh(["bsdtar", "-acf", at("loose.tar.zst"), "-C", at("-odd dir"), "a.txt", "sub"]).status, 0)
  assert.equal(sh(A.extractCommand(at("loose.tar.zst"), at("out", "loose"))).status, 0)
  assert.deepEqual(tree(at("out", "loose")), ["a.txt", "sub", "sub/b.txt"])
  assert.equal(fs.statSync(at("out", "loose")).mode & 0o777, fs.statSync(at("out")).mode & 0o777, "an extract changed the folder's mode")
  fs.writeFileSync(at("broken.zip"), "not an archive")
  assert.notEqual(sh(A.extractCommand(at("broken.zip"), at("out", "broken"))).status, 0)
  assert.deepEqual(fs.readdirSync(at("out")).sort(), ["-odd dir", "-odd dir.zip", "loose"], "a failed extract left something")

  // Convert checks its name before handing over to the transcoder.
  calls.length = 0
  find(find(menu(file("p.jpg", { path: at("out", "p.jpg") }), { image: true }), "convert").sub, "as:jpg-medium").run()
  const [, check, about] = calls[0]
  assert.deepEqual([about.name, about.then], ["p-medium.jpg", ["omarchy-transcode", at("out", "p.jpg"), "jpg", "medium"]])
  assert.equal(sh(check).status, 0)
  fs.writeFileSync(at("out", "p-medium.jpg"), "x")
  assert.equal(sh(check).status, 17, "a conversion would overwrite")

  // Duplicate copies and Make link points, each under the name typed, and neither overwrites.
  const real = { panel: { listedDir: at("out") }, note() {} }
  real.run = (command, about) => { real.about = about; real.status = sh(command).status }
  for (const name of ["guarded", "inHere", "pasteCommand", "paste"]) real[name] = method(opsSource, name, { root: real })
  for (const [verb, name] of [["copy", "loose copy"], ["link", "loose link"]])
    for (const status of [0, 17]) {
      const naming = { naming: verb, renameTo: name, named: { name: "loose", path: at("out", "loose") } }
      method(panelSource, "commitName", { root: naming, ops: real })()
      assert.equal(real.status, status, verb + (status ? " overwrote" : ""))
    }
  assert.deepEqual(tree(at("out", "loose copy")), ["a.txt", "sub", "sub/b.txt"])
  assert.equal(fs.readlinkSync(at("out", "loose link")), at("out", "loose"))
  // An entry of a folder's preview is duplicated beside itself, and nothing lands in the folder listed.
  const aside = { naming: "copy", renameTo: "a copy.txt", named: { name: "a.txt", path: at("-odd dir", "a.txt") } }
  method(panelSource, "commitName", { root: aside, ops: real })()
  assert.deepEqual([real.status, real.about.land, fs.readFileSync(at("-odd dir", "a copy.txt"), "utf8")], [0, false, "a"])

  // Paste into a folder row lands nothing in view and says where it went.
  fs.writeFileSync(at("moving.txt"), "m")
  real.held = { items: [{ path: at("moving.txt"), name: "moving.txt" }], name: "moving.txt", move: true }
  real.paste(at("out", "loose"))
  assert.deepEqual([real.status, real.about.land, real.about.done], [0, false, "moved moving.txt into loose"])
  assert.equal(fs.readFileSync(at("out", "loose", "moving.txt"), "utf8"), "m")
  fs.writeFileSync(at("moving.txt"), "again")
  real.paste(at("out", "loose"))
  assert.equal(real.status, 17, "a paste into a folder overwrote")

  // Many paste in one process, past a name already taken, and say so.
  fs.mkdirSync(at("dest"))
  fs.writeFileSync(at("m1.txt"), "1"); fs.writeFileSync(at("m2 '$x'.txt"), "2"); fs.writeFileSync(at("dest", "m2 '$x'.txt"), "keep")
  real.panel.listedDir = at("dest")
  real.held = { items: [{ path: at("m1.txt"), name: "m1.txt" }, { path: at("m2 '$x'.txt"), name: "m2 '$x'.txt" }], move: true, name: "2 items" }
  real.paste()
  assert.deepEqual([real.status, real.about.taken, real.about.done, real.about.land], [18, "some names were already here; the rest moved", "moved 2 items", true])
  assert.deepEqual([fs.readFileSync(at("dest", "m1.txt"), "utf8"), fs.existsSync(at("m1.txt")), fs.readFileSync(at("dest", "m2 '$x'.txt"), "utf8"),
                    fs.readFileSync(at("m2 '$x'.txt"), "utf8")], ["1", false, "keep", "2"], "a paste of many overwrote, or did not go on")
  fs.writeFileSync(at("m3.txt"), "3")
  real.held = { items: [{ path: at("m3.txt"), name: "m3.txt" }, { path: at("m2 '$x'.txt"), name: "m2 '$x'.txt" }], move: false, name: "2 items" }
  real.panel.listedDir = at("out")
  real.paste()
  assert.deepEqual([real.status, fs.readFileSync(at("out", "m3.txt"), "utf8"), fs.existsSync(at("m3.txt"))], [0, "3", true])
  // Every name taken is 17, as for one: nothing went, so a move keeps its hold and none "moved".
  real.paste()
  assert.equal(real.status, 17, "a paste of many with every name taken said some went")
} finally {
  fs.rmSync(base, { recursive: true, force: true })
}
console.log("ok: compress, extract, convert, duplicate, link and paste-into never overwrite, and clean up after a failure")

// Trash arms for the exact list it was given: another list, even a part of it, arms anew.
const trashed = []
const trashing = { panel: { editing: false, sel: null, home: "/home/t" }, doomed: "", note() {}, run: (c, about) => trashed.push([[...c], about.done]) }
for (const name of ["label", "remove", "copyPath"])
  trashing[name] = method(opsSource, name, { root: trashing, doomArmed: { restart() {} }, FilesIndex: { display: p => p } })
// Del in an empty folder, or with a filter matching nothing, has nothing to arm.
trashing.remove([]); trashing.copyPath([])
assert.deepEqual([trashing.doomed, trashed.length], ["", 0], "nothing selected was armed, trashed or copied")
const two = [{ path: "/d/a", name: "a" }, { path: "/d/b", name: "b" }]
trashing.remove(two)
assert.deepEqual([trashing.doomed, trashed.length], ["/d/a\n/d/b", 0])
trashing.remove([two[0]]); trashing.remove(two)
assert.deepEqual([trashing.doomed, trashed.length], ["/d/a\n/d/b", 0], "a different list confirmed the armed one")
trashing.remove(two)
assert.deepEqual(trashed.pop(), [["gio", "trash", "--", "/d/a", "/d/b"], "trashed 2 items"])
trashing.copyPath(two)
assert.deepEqual(trashed.pop(), [["sh", "-c", 'printf %s "$1" | wl-copy', "files", "/d/a\n/d/b"], "copied 2 paths"])
console.log("ok: trash arms for exactly its list, and many paths copy one to a line")
