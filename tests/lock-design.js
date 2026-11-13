// The design command lists scenes and persists a valid choice. A folder without a scene is no design.
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { spawnSync } = require("node:child_process")
const { repo } = require("./qml.js")

const home = fs.mkdtempSync(path.join(os.tmpdir(), "lock-design-"))
const design = (...args) => spawnSync(path.join(repo, "bin/omarchy-lock-design"), args,
  { env: { ...process.env, HOME: home }, encoding: "utf8" })
const choice = path.join(home, ".config/wheely/lock-design")
try {
  for (const name of ["rally", "meadow", "notes"]) {
    const folder = path.join(home, ".local/share/wheely/lock", name)
    fs.mkdirSync(folder, { recursive: true })
    if (name !== "notes") fs.writeFileSync(path.join(folder, "Scene.qml"), "")
  }
  assert.equal(design("list").stdout, "meadow\nrally\n")
  assert.equal(design("current").stdout, "wallpaper\n", "with no choice yet the lock screen shows wallpaper")
  assert.equal(design("set", "meadow").status, 0)
  assert.deepEqual([fs.readFileSync(choice, "utf8"), design("current").stdout], ["meadow\n", "meadow\n"])
  fs.mkdirSync(path.join(home, "elsewhere"))
  fs.writeFileSync(path.join(home, "elsewhere/Scene.qml"), "")
  for (const args of [["set", "missing"], ["set", "../../../../elsewhere"], []]) {
    assert.equal(design(...args).status, 1, args.join(" "))
    assert.equal(fs.readFileSync(choice, "utf8"), "meadow\n", "a refused choice replaced the design")
  }
} finally {
  fs.rmSync(home, { recursive: true, force: true })
}
const view = fs.readFileSync(path.join(repo, "patches/shell/plugins/lock/LockView.qml"), "utf8")
const named = text => new Function("chosen", "return " + view.match(/property string design: (.+)/)[1])({ text: () => text })
assert.deepEqual(["meadow\n", "", "../../../../elsewhere\n", "/tmp/x"].map(named), ["meadow", "wallpaper", "wallpaper", "wallpaper"])
console.log("ok: designs are listed and chosen by name, wallpaper until one is, and a bad name or a path changes nothing")
