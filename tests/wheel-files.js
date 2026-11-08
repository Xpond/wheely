// File rows need no desktop: sigils, fd's trailing slash, payloads and use keys. Run: node tests/wheel-files.js
const assert = require("node:assert/strict")
const { M } = require("./wheel-source.js")

const home = "/home/test"
assert.equal(M.termOf("/wheel"), "wheel", "a leading sigil was kept")
assert.equal(M.termOf("wheel"), "wheel", "a sigil was stripped where none led")

// fd uses a trailing slash to distinguish directories.
const scanned = M.parseFiles([`${home}/Downloads/`, `${home}/.config/hypr/hyprland.conf`].join("\0"))
const dir = M.fileRows(scanned, "downloads", 1, home)[0]
const file = M.fileRows(scanned, "hyprland", 1, home)[0]
assert.ok(dir && dir.label === "Downloads" && dir.trail === "~",
  "a directory row is not named without its trailing slash: " + JSON.stringify(dir))
assert.ok(file && file.label === "hyprland.conf" && file.trail === "~/.config/hypr",
  "a file row does not carry the directory above it, relative to home: " + JSON.stringify(file))
assert.notEqual(dir.icon, file.icon, "files and directories wear the same mark")

assert.equal(M.pathPayload(`${home}/a/b.txt`), JSON.stringify({ dir: `${home}/a`, select: "b.txt" }),
  "a file payload does not name its directory and itself")
assert.equal(M.pathPayload(`${home}/a/`), JSON.stringify({ dir: `${home}/a` }),
  "a directory payload does not name itself and select nothing")

assert.equal(M.keyOf(M.fileRow(`${home}/a.txt`, home)), `file:${home}/a.txt`, "a file is not counted by its path")
console.log("ok: sigils strip once, file rows name themselves and their folder, payloads and use keys follow the path")
