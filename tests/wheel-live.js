#!/usr/bin/env node
// Check wheel invariants against this machine's real menu.

const fs = require("fs")
const path = require("path")
const { execSync, spawnSync } = require("child_process")

const here = path.join(__dirname, "../plugins/xpo.wheel")
const omarchy = process.env.OMARCHY_PATH || "/usr/share/omarchy"
const home = process.env.HOME

// Collect declarations because a QML library cannot be imported by Node.
const src = fs.readFileSync(path.join(here, "MenuIndex.js"), "utf8").replace(/^\.pragma library/m, "")
const names = [...src.matchAll(/^(?:function (\w+)|var (\w+) =)/gm)].map(m => m[1] || m[2])
const M = new Function(src + "\nreturn {" + names.join(",") + "}")()

const read = p => { try { return fs.readFileSync(p, "utf8") } catch { return "" } }
let failed = 0
const check = (ok, label, detail) => {
  console.log(`${ok ? "ok  " : "FAIL"}  ${label}`)
  if (!ok) { failed++; if (detail) console.log("        " + detail) }
}

const items = M.merge(
  M.menuOf(read(`${omarchy}/default/omarchy/omarchy-menu.jsonc`)),
  M.menuOf(read(`${home}/.config/omarchy/extensions/omarchy-menu.jsonc`)))
check(Object.keys(items).length > 0, "menu definitions load",
      `nothing parsed from ${omarchy}/default/omarchy/omarchy-menu.jsonc`)

const scan = execSync("bash", { input: M.conditionScript(items), encoding: "utf8", maxBuffer: 1 << 22 })
const cond = M.parseConditions(scan, items)

// Scan every caller; ignore the library URL in imports and worker sources.
const callers = fs.readdirSync(here)
  .filter(f => /\.(qml|js)$/.test(f) && f !== "MenuIndex.js")
  .map(f => fs.readFileSync(path.join(here, f), "utf8").replace(/^import .*$/gm, "")
    .replace(/(["'])MenuIndex\.js\1/g, "")).join("\n")
const missing = [...new Set([...callers.matchAll(/MenuIndex\.(\w+)/g)].map(m => m[1]))]
  .filter(n => M[n] === undefined)
check(missing.length === 0, "every call site names something MenuIndex.js defines", missing.join(", "))

check(M.parseConditions("", items).ready === false, "an empty condition scan fails open")

// The batch answers package checks and shared readers its own way; each check asked alone must agree.
const alone = []
for (const id in items)
  for (const [tag, test] of [["w", items[id].when], ["c", items[id].checked]])
    if (test && spawnSync("bash", ["-c", `{ ${test}; } >/dev/null 2>&1`]).status === 0) alone.push(`${id}:${tag}`)
const batched = M.lines(scan)
check(JSON.stringify(batched.sort()) === JSON.stringify(alone.sort()),
      `the batched checks agree with asking each alone (${alone.length} hold)`,
      `only batched: ${batched.filter(l => !alone.includes(l))}; only alone: ${alone.filter(l => !batched.includes(l))}`)

const rows = M.menuRows(items, cond)
const emitted = new Set(rows.map(r => r.id))
const unreachable = Object.keys(items).filter(id => {
  const e = items[id]
  if (!M.passes(e, id, cond)) return false              // its `when` failed: not available here
  if (!e.action && !e.provider && !cond.full[id]) return false  // submenu its children emptied
  return !emitted.has(id)
})
check(unreachable.length === 0,
      `every available menu is searchable (${Object.keys(items).length} entries -> ${rows.length} rows)`,
      unreachable.join(", "))

const dead = rows.filter(r => !r.action && !r.node)
check(dead.length === 0, "every row has something to do", dead.map(r => r.label).join(", "))

const empty = rows.filter(r => r.node && M.ringSlices(items, r.node.split("."), cond, []).length === 0)
check(empty.length === 0, "no row drills into an empty ring", empty.map(r => r.id).join(", "))

// Every keybinding, read with the wheel's own command, is one search away: its description finds
// a row that runs its command, whether a row of its own or one it joined.
const bindCommand = JSON.parse(fs.readFileSync(path.join(here, "Wheel.qml"), "utf8")
  .match(/id: bindList[^]*?command: (\[.*\])/)[1])
const binds = M.bindRows(spawnSync(bindCommand[0], bindCommand.slice(1), { encoding: "utf8" }).stdout)
check(binds.length > 0, `keybindings load (${binds.length} runnable)`, "no records from omarchy-menu-keybindings")
const fixed = [...M.panelRows([...M.panels(null), ...M.EXTRAS]), ...rows,
               ...M.settingRows(M.SHORTCUT, false, [], M.SKIPPED, 0, true, M.PAUSE_KEY)]
// Windows are uncounted because every launch has a new address.
const counted = M.withBindings(fixed, binds, items)
const unfound = binds.filter(b => !M.search(counted, b.label, Infinity, {})
  .some(r => [r.dispatch, ...M.bindTargets(r, items)].includes(b.action || b.dispatch)))
const joined = fixed.filter((r, i) => counted[i] !== r).length
check(unfound.length === 0, `every keybinding is found by its description `
      + `(${counted.length - fixed.length} own rows, ${joined} joined)`, unfound.map(b => b.label).join(", "))

const keyless = counted.filter(r => !M.keyOf(r))
check(keyless.length === 0, "every counted row has a use key", keyless.map(r => r.label).join(", "))

const keys = counted.map(r => M.keyOf(r))
const collided = keys.filter((k, i) => keys.indexOf(k) !== i)
check(collided.length === 0, `use keys are unique (${keys.length} keys)`, collided.join(", "))

check(M.keyOf({ label: "a window", address: "0x1" }) === "", "windows are not counted")

const shadowed = rows.filter(r => M.modeOf(r.label))
check(shadowed.length === 0, `no menu label starts with a mode sigil (${Object.keys(M.MODES).join(" ")})`,
      shadowed.map(r => r.label).join(", "))
check(M.termOf("/wheel") === "wheel" && M.termOf("wheel") === "wheel",
      "a sigil is stripped exactly once, and only when it leads")

// fd uses a trailing slash to distinguish directories.
const scanned = M.parseFiles(`${home}/Downloads/\n${home}/.config/hypr/hyprland.conf\n`)
const dir = M.fileRows(scanned, "downloads", 1, home)[0]
const file = M.fileRows(scanned, "hyprland", 1, home)[0]
check(!!dir && dir.label === "Downloads" && dir.trail === "~",
      "a directory row is named without its trailing slash", JSON.stringify(dir))
check(!!file && file.label === "hyprland.conf" && file.trail === "~/.config/hypr",
      "a file row carries the directory above it, relative to home", JSON.stringify(file))
check(!!dir && dir.icon !== file.icon, "files and directories wear different marks")

check(M.pathPayload(`${home}/a/b.txt`) === JSON.stringify({ dir: `${home}/a`, select: "b.txt" }),
      "a file payload names its directory and itself", M.pathPayload(`${home}/a/b.txt`))
check(M.pathPayload(`${home}/a/`) === JSON.stringify({ dir: `${home}/a` }),
      "a directory payload names itself and selects nothing", M.pathPayload(`${home}/a/`))

check(M.keyOf(M.fileRow(`${home}/a.txt`, home)) === `file:${home}/a.txt`, "a file is counted by its path")

// An odd ring is allowed, but worth knowing about: it has no slice at 3 or 9 o'clock.
for (const [label, cfg] of [["shipped", `${omarchy}/config/omarchy/shell.json`],
                            ["this machine", `${home}/.config/omarchy/shell.json`]]) {
  const raw = read(cfg)
  if (!raw) continue
  const n = M.panels(M.barWidgets(raw)).length
  if (n % 2) console.log(`note  ${label} bar's slices are not even on the wheel (${n}): none sits at 3 or 9 o'clock`)
}

console.log(failed ? `\n${failed} failed` : "\nall good")
process.exit(failed ? 1 : 0)
