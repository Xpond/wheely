// Also loaded by WorkerScript so file indexing and ranking stay off the UI thread.

// Match the shell's JSONC parsing; malformed input leaves the wheel usable.
function parse(raw) {
  try {
    return JSON.parse(String(raw || "")
      .replace(/^\s*\/\/[^\n]*(\n|$)/gm, "")
      .replace(/,(\s*[}\]])/g, "$1")) || {}
  } catch (e) {
    return {}
  }
}

// Only objects are entries, as Omarchy reads a menu file: a null or a string never replaces a default.
function menuOf(raw) {
  var cfg = parse(raw), out = {}
  for (var id in cfg) if (cfg[id] && typeof cfg[id] === "object" && !Array.isArray(cfg[id])) out[id] = cfg[id]
  return out
}

function merge(defaults, user) {
  var out = {}
  for (var a in defaults) out[a] = defaults[a]
  for (var b in user) out[b] = user[b]
  return out
}

// Dotted ids encode the menu hierarchy.
function trailOf(items, id) {
  var parts = String(id).split(".")
  var trail = []
  for (var i = 1; i < parts.length; i++) {
    var parent = items[parts.slice(0, i).join(".")]
    if (parent && parent.label) trail.push(parent.label)
  }
  return trail
}

// Search kind precedence.
var KIND = { slice: 0, window: 1, app: 2, style: 3, menu: 4, bind: 5, manual: 6 }

// Prefer stable ids for use counts; windows already sort by live focus.
function keyOf(e) {
  if (e.setting) return "setting:" + e.setting
  if (e.path) return "file:" + e.path
  if (e.plugin) return e.plugin
  if (e.id) return e.id
  if (e.appId) return "app:" + e.appId
  return e.action || e.dispatch || ""
}

// Keep the selected action through a refresh; a reused menu id with a new command is a new action.
function indexOfEntry(rows, previous) {
  if (!previous) return -1
  var key = keyOf(previous)
  for (var i = 0; i < rows.length; i++) {
    var e = rows[i]
    if (keyOf(e) === key && e.action === previous.action
        && e.address === previous.address && e.path === previous.path) return i
  }
  return -1
}

function crumb(items, path) {
  var out = []
  for (var i = 0; i < path.length; i++) {
    var e = items[path.slice(0, i + 1).join(".")]
    out.push((e && e.label) || path[i])
  }
  return out.join(" \u203a ")
}

function lines(raw) {
  var out = []
  var parts = String(raw || "").split("\n")
  for (var i = 0; i < parts.length; i++) {
    var value = parts[i].trim()
    if (value) out.push(value)
  }
  return out
}

// Shell-quote names.
function quote(value) {
  return "'" + String(value).replace(/'/g, "'\\''") + "'"
}

// Prefer observed focus order, then Hyprland's cached history.
function recencyOf(order, address, cachedHistory) {
  var seen = order.indexOf(address)
  return seen >= 0 ? seen : order.length + (Number(cachedHistory) || 0)
}

function styleRows(out, names, current, icon, trail, command) {
  for (var i = 0; i < names.length; i++) {
    var name = String(names[i])
    out.push({
      icon: icon, label: name + (name === current ? " ✓" : ""), trail: trail, kind: KIND.style,
      action: command + quote(name),
      keywords: (name + " " + trail).toLowerCase()
    })
  }
}

// Themes and fonts fire `omarchy theme|font set`; the current one is marked.
function styles(themes, theme, fonts, font) {
  var out = []
  styleRows(out, themes, theme, "󰸌", "Theme", "omarchy theme set ")
  styleRows(out, fonts, font, "󰛖", "Font", "omarchy font set ")
  return out
}

// Lock-screen designs as one Style submenu: search finds it, and each design shows only inside it.
function lockItems(names) {
  if (!names.length) return {}
  var out = { "style.lockscreen": { icon: "󰌾", label: "Lockscreen Designs" } }
  for (var i = 0; i < names.length; i++) {
    var name = names[i]
    out["style.lockscreen." + i] = { icon: "󰋩", label: name.charAt(0).toUpperCase() + name.slice(1),
                                     action: "omarchy-lock-design set " + quote(name), search: false,
                                     checked: "[[ $(omarchy-lock-design current) == " + quote(name) + " ]]" }
  }
  return out
}

// Shell panels in ring order; branded marks use their own QML components.
var PANELS = [
  { plugin: "omarchy.audio", icon: "󰕾", label: "Audio" },
  { plugin: "omarchy.network", icon: "󰖩", label: "Network" },
  { plugin: "omarchy.bluetooth", icon: "󰂯", label: "Bluetooth" },
  { plugin: "omarchy.monitor", icon: "󰍹", label: "Display" },
  { plugin: "omarchy.clock", icon: "󰃭", label: "Calendar" },
  { plugin: "omarchy.tailscale", icon: "", iconFile: "tailscale/TailscaleIcon.qml", label: "Tailscale" },
  { plugin: "omarchy.agents", icon: "󱚣", label: "Agents" },
  { plugin: "omarchy.dropbox", icon: "", iconFile: "dropbox/DropboxIcon.qml", label: "Dropbox" },
  { plugin: "omarchy.power", icon: "󰂄", label: "Power" }
]

// Overlays are available independently of the bar layout.
var OVERLAYS = [
  { plugin: "omarchy.clipboard", icon: "", label: "Clipboard" }
]

// Searchable without adding another default ring slice.
var EXTRAS = [
  { plugin: "xpo.files", icon: "󰉋", label: "Files",
    keywords: "file manager browser folder directory explorer nautilus" }
]

// Searchable panels kept off the default ring so its count stays even.
var SEARCH_PANELS = [
  { plugin: "omarchy.weather", icon: "", label: "Weather" }
]

// Clones keep their source's mark; unknown panels get a generic one. Panels
// that already have a fixed search row are not repeated.
function livePanels(live) {
  var marks = {}, fixed = {}
  var known = PANELS.concat(SEARCH_PANELS)
  for (var i = 0; i < known.length; i++) marks[known[i].plugin] = known[i]
  var rows = OVERLAYS.concat(EXTRAS)
  for (var k = 0; k < rows.length; k++) fixed[rows[k].plugin] = true
  var out = []
  for (var j = 0; j < live.length; j++) {
    var p = live[j]
    if (fixed[p.id]) continue
    var mark = marks[p.source] || { icon: "󰕮" }
    out.push({ plugin: p.id, icon: mark.icon, iconFile: mark.iconFile,
               label: p.id === mark.plugin ? mark.label : p.name,
               keywords: p.name + " " + (mark.label || "") })
  }
  return out
}

// A list wheel.json keeps, or null for its default: an empty list is the default too.
function listIn(raw, key) {
  var list = parse(raw)[key]
  return list && list.length ? list : null
}

function barWidgets(raw) {
  var cfg = parse(raw)
  var layout = (cfg.bar && cfg.bar.layout) || null
  if (!layout) return null
  var ids = {}
  for (var section in layout) {
    var row = layout[section]
    if (!row) continue
    // Omarchy takes a widget as its id alone or as an object carrying one.
    for (var i = 0; i < row.length; i++) {
      var id = typeof row[i] === "string" ? row[i] : row[i] && row[i].id
      if (id) ids[id] = true
    }
  }
  return ids
}

// Bar membership chooses default slices; PANELS keeps their order stable.
function panels(barIds) {
  var out = []
  for (var i = 0; i < PANELS.length; i++)
    if (!barIds || barIds[PANELS[i].plugin]) out.push(PANELS[i])
  return out.concat(OVERLAYS)
}

var CONDITION_READERS = [
  "omarchy-default-agent", "omarchy-default-browser", "omarchy-default-terminal", "omarchy-default-editor",
  "omarchy-dns", "omarchy-channel-current", "omarchy-lock-design current", "dell-xps-touchpad-haptics get"
]

// Every `when` and `checked` in one bash script, echoing `<id>:w` or `<id>:c` for each that holds.
// Asked one at a time the package checks alone take over a second, so one `pacman -T` answers
// every name they ask about, and known readers in simple comparisons run once.
function conditionScript(items) {
  var checks = [], names = {}, reads = []
  for (var id in items) {
    var tags = { w: items[id].when, c: items[id].checked }
    for (var tag in tags) {
      if (!tags[tag]) continue
      var expr = String(tags[tag])
      var asked = /omarchy-pkg-(?:present|missing)((?:[ \t]+[\w@.+-]+)+)/g, m
      while ((m = asked.exec(expr))) m[1].trim().split(/\s+/).forEach(function (n) { names[n] = true })
      // Only a whole comparison of a known reader and literal/pattern can share its output.
      // Assignments, guards, quoted shell text and arbitrary commands keep their Bash semantics.
      var comparison = /^\[\[ ("?)\$\(([\w .-]+)\)\1 == ("[\w .\/-]*"|'[\w .\/-]*'|[\w.*\/-]+) \]\]$/.exec(expr)
      if (comparison && CONDITION_READERS.indexOf(comparison[2]) >= 0) {
        var read = comparison[2]
        if (reads.indexOf(read) < 0) reads.push(read)
        expr = "[[ " + comparison[1] + "${__read" + reads.indexOf(read) + "}" + comparison[1]
             + " == " + comparison[3] + " ]]"
      }
      checks.push("if { " + expr + "; } >/dev/null 2>&1; then echo " + id + ":" + tag + "; fi")
    }
  }
  var pkgs = Object.keys(names)
  // Asked names start installed and pacman -T prints those that are not; any other name, or a
  // query that failed, asks pacman itself, as omarchy-pkg-present does.
  var head = [
    "declare -A __pkg=(" + pkgs.map(function (n) { return "[" + n + "]=1" }).join(" ") + ")",
    "__missing=$(pacman -T -- " + pkgs.join(" ") + " 2>/dev/null)",
    "case $? in 0|127) for __p in $__missing; do __pkg[$__p]=0; done ;; *) __pkg=() ;; esac",
    "__has() { case ${__pkg[$1]-} in 1) return 0 ;; 0) return 1 ;; esac; pacman -Q \"$1\" &>/dev/null; }",
    "omarchy-pkg-present() { local p; for p; do __has \"$p\" || return 1; done; }",
    "omarchy-pkg-missing() { local p; for p; do __has \"$p\" || return 0; done; return 1; }"
  ]
  for (var r = 0; r < reads.length; r++) head.push("__read" + r + "=$(" + reads[r] + " 2>/dev/null)")
  return head.concat(checks).join("\n")
}

var NO_CONDITIONS = { when: {}, checked: {}, full: {}, ready: false }

// Empty output signals evaluation failure; keep conditional rows visible.
function parseConditions(raw, items) {
  var ls = lines(raw)
  if (!ls.length) return NO_CONDITIONS
  var cond = { when: {}, checked: {}, ready: true }
  for (var i = 0; i < ls.length; i++) {
    var at = ls[i].lastIndexOf(":")
    var holds = ls[i].slice(at + 1) === "c" ? cond.checked : cond.when
    holds[ls[i].slice(0, at)] = true
  }
  cond.full = populated(items, cond)
  return cond
}

function passes(e, id, cond) {
  return !e.when || !cond.ready || cond.when[id] === true
}

// Mark ancestors of surviving actions so empty submenus stay hidden.
function populated(items, cond) {
  var out = {}
  for (var id in items) {
    var e = items[id]
    if (!e || (!e.action && !e.provider) || !passes(e, id, cond)) continue
    var parts = id.split(".")
    for (var i = parts.length - 1; i >= 1; i--) {
      var pid = parts.slice(0, i).join(".")
      var parent = items[pid]
      if (parent && !passes(parent, pid, cond)) break
      out[pid] = true
    }
  }
  return out
}

function shows(id, e, cond) {
  if (!passes(e, id, cond)) return false
  return e.action || e.provider || !cond.ready || cond.full[e.target || id] === true
}

// Providers hand off to Omarchy; nodes carry the id the ring drills into, a link its target's.
// Omarchy's own marks sit in a font of their own, at codepoints a Nerd Font fills with other glyphs.
function entryOf(id, e, cond) {
  var s = { id: id, icon: e.icon || "󰍜", label: (e.label || id) + (cond.checked[id] ? " ✓" : "") }
  if (e.iconFont) s.iconFont = e.iconFont
  if (e.action) s.action = e.action
  else if (e.provider) s.action = "omarchy-menu summon " + id
  else s.node = e.target || id
  return s
}

function childrenOf(items, parent, cond) {
  var prefix = parent ? parent + "." : ""
  var depth = parent ? parent.split(".").length + 1 : 1
  var out = []
  for (var id in items) {
    if (id.indexOf(prefix) !== 0 || id.split(".").length !== depth) continue
    var e = items[id]
    if (!shows(id, e, cond)) continue
    out.push(entryOf(id, e, cond))
  }
  return out
}

// A ring holds what search finds and keeps a key of its own: no window, file, answer or setting.
function pinnable(e) {
  return !!keyOf(e) && !e.setting && !e.path
}

function pinnableByKey(index) {
  var byKey = {}
  for (var i = 0; i < index.length; i++) if (pinnable(index[i])) byKey[keyOf(index[i])] = index[i]
  return byKey
}

// The ring's keys as the search rows they name, in order; a key that names nothing is dropped.
function ringOf(index, keys) {
  var byKey = pinnableByKey(index)
  var out = []
  for (var j = 0; j < keys.length; j++) if (byKey[keys[j]]) out.push(byKey[keys[j]])
  return out
}

// A pick moves its key last, so the uses file reads oldest to newest and history needs no clock.
function withPick(uses, key) {
  var out = {}
  for (var k in uses) if (k !== key) out[k] = uses[k]
  out[key] = (uses[key] || 0) + 1
  return out
}

// Picks newest first: a file by its path, anything else as search finds it. Settings, and keys
// that name nothing today, are left out.
function historyRows(index, uses, home) {
  var byKey = pinnableByKey(index)
  return Object.keys(uses).reverse().map(function (k) {
    return k.indexOf("file:") === 0 ? fileRow(k.slice(5), home) : byKey[k]
  }).filter(Boolean)
}

// wheel.json with one list replaced, or gone back to its default; anything else in it stays.
function withList(raw, key, list) {
  var cfg = parse(raw)
  if (list) cfg[key] = list
  else delete cfg[key]
  return JSON.stringify(cfg, null, 2) + "\n"
}

// A ring of directions puts each where it points: the first slice is north, then clockwise.
var COMPASS = ["top", "right", "bottom", "left"]

function ringSlices(items, path, cond, ring) {
  if (!path.length) return ring
  var out = childrenOf(items, path.join("."), cond)
  var at = function (s) { return COMPASS.indexOf(s.label.toLowerCase()) }
  return out.every(function (s) { return at(s) >= 0 }) ? out.sort(function (a, b) { return at(a) - at(b) }) : out
}

function panelRows(panels) {
  var out = []
  for (var i = 0; i < panels.length; i++) {
    var p = panels[i]
    out.push({ icon: p.icon, iconFile: p.iconFile, label: p.label, trail: "Panel",
               kind: KIND.slice, plugin: p.plugin,
               keywords: (p.label + " " + (p.keywords || "")).toLowerCase() })
  }
  return out
}

// Cache flattened menu rows separately from sources that change on every open.
function menuRows(items, cond) {
  var out = []
  for (var id in items) {
    var e = items[id]
    if (!e || e.search === false || !shows(id, e, cond)) continue
    var trail = trailOf(items, id)
    var row = entryOf(id, e, cond)
    row.trail = trail.join(" › ")
    row.kind = KIND.menu
    row.keywords = [e.label, trail.join(" "), String(id).replace(/[.]/g, " "),
                    [].concat(e.aliases || []).join(" "), e.description || ""]
                   .join(" ").toLowerCase()
    out.push(row)
  }
  return out
}

function liveRows(sources) {
  var out = []
  // App rows launch by desktop id and carry icon names.
  var apps = sources.apps
  var iconByAppId = {}
  for (var j = 0; j < apps.length; j++) {
    var a = apps[j].entry
    if (!a.id) continue
    var name = String(a.name || a.id)
    var appIcon = String(a.icon || a.id)
    iconByAppId[String(a.id).toLowerCase()] = appIcon
    out.push({
      icon: "󰖯", appIcon: appIcon, label: name, trail: "App",
      appId: String(a.id), kind: KIND.app,
      keywords: [name, a.genericName || "",
                 a.keywords && a.keywords.join ? a.keywords.join(" ") : ""]
                .join(" ").toLowerCase(),
      // Search only the dotted id tail as whole words.
      ident: String(a.id).split(".").pop().replace(/[_-]/g, " ").toLowerCase()
    })
  }
  // Store window addresses, and resolve icons through matching desktop entries. The trail names
  // the live workspace (lastIpcObject's goes stale) and is searchable: "workspace" lists windows.
  var windows = sources.windows
  for (var w = 0; w < windows.length; w++) {
    var t = windows[w]
    var ipc = t.lastIpcObject || {}
    var appId = String((t.wayland && t.wayland.appId) || "")
    var title = String(t.title || appId)
    if (!title) continue
    var where = t.workspace ? "Workspace " + t.workspace.name.replace(/^special:/, "") : "Window"
    out.push({
      icon: "󰖯", appIcon: iconByAppId[appId.toLowerCase()] || "", label: title,
      trail: where + (appId ? " · " + appId : ""), address: "0x" + t.address,
      kind: KIND.window,
      recency: recencyOf(sources.focusOrder, t.address, ipc.focusHistoryID),
      keywords: (title + " " + appId + " " + where).toLowerCase()
    })
  }
  return out
}

// The wheel's own bindings (open, commit, close) mean nothing from inside it.
var WHEEL_BIND = /xpo\.wheel|omarchy-wheel-close/

// Omarchy's keybinding records, `KEYS → Description<TAB>kind<TAB>arg`, as rows. Exec and Lua binds
// run from a row; a sendshortcut needs its web app focused, and a mouse bind needs the mouse.
function bindRows(raw) {
  var out = []
  var ls = lines(raw)
  for (var i = 0; i < ls.length; i++) {
    var f = ls[i].split("\t")
    var at = f[0].indexOf("→")
    if (at < 0 || /mouse/i.test(f[0].slice(0, at)) || !f[2] || (f[1] !== "exec" && f[1] !== "lua")
        || WHEEL_BIND.test(f.slice(2).join("\t"))) continue
    var label = f[0].slice(at + 1).trim()
    var row = { icon: "", label: label, trail: "", kind: KIND.bind,
                keywords: label.toLowerCase() }
    row[f[1] === "lua" ? "dispatch" : "action"] = f.slice(2).join("\t")
    out.push(row)
  }
  return out
}

// What a binding runs to do what a row does: toggle its panel, run its command, or open
// Omarchy's menu at it by id or alias.
function bindTargets(row, items) {
  if (row.plugin) return ["omarchy-shell shell toggle " + row.plugin]
  var out = row.action ? [row.action] : []
  var routes = row.id ? [row.id].concat(items[row.id].aliases || []) : []
  for (var i = 0; i < routes.length; i++) out.push("omarchy-menu toggle " + routes[i])
  return out
}

// One action is one row: a binding that runs what a row runs lends that row its description as
// search words, and the rest join as rows of their own. Rows outlive an open, so a lent row is a copy.
function withBindings(rows, binds, items) {
  var out = rows.slice()
  var at = {}
  for (var i = 0; i < out.length; i++) {
    var targets = bindTargets(out[i], items)
    for (var t = 0; t < targets.length; t++) if (at[targets[t]] === undefined) at[targets[t]] = i
  }
  for (var b = 0; b < binds.length; b++) {
    var bind = binds[b]
    var command = bind.action || bind.dispatch
    var j = at[command]
    if (j === undefined) { at[command] = out.length; out.push(bind); continue }
    out[j] = merge(out[j], { keywords: out[j].keywords + " " + bind.keywords, _search: null })
  }
  return out
}

// Every wheel setting wears the wheel's own ring of dots, which nothing in Omarchy wears.
var SETTING_ICON = "󱥸"

// Wheel settings are search rows: `wheely settings` lists them, and each is changed in place.
// Wheely history rides along, answering to `history` rather than `settings`. The wallpaper pause
// row comes with Wheelie, the theme whose scene it pauses: without its key, the row is left out.
function settingRows(shortcut, customRing, folders, skipped, picks, centered, pauseKey) {
  return [{ icon: SETTING_ICON, label: "Wheely shortcut", trail: shortcut, kind: KIND.slice, setting: "shortcut",
            keywords: "wheely settings preferences shortcut keybinding keybind hotkey key launch open" },
          { icon: SETTING_ICON, label: "Wallpaper pause", trail: pauseKey, kind: KIND.slice, setting: "pause",
            keywords: "wheely settings preferences wallpaper wheelie tidal pause resume shortcut keybinding keybind hotkey key" },
          { icon: SETTING_ICON, label: "Wheely ring", trail: customRing ? "Custom" : "Bar", kind: KIND.slice,
            setting: "ring", keywords: "wheely settings preferences ring slices discs pin unpin order favorites" },
          { icon: SETTING_ICON, label: "Backdrop", trail: "", kind: KIND.slice, setting: "backdrop",
            keywords: "wheely settings preferences backdrop background blur dim darken frost glass scrim tint" },
          { icon: SETTING_ICON, label: "Centered panels", trail: centered ? "On" : "Off", kind: KIND.slice, setting: "panels",
            keywords: "wheely settings preferences centered center middle panels popups native bar position" },
          { icon: SETTING_ICON, label: "Searched folders", trail: "Home" + (folders.length ? " + " + folders.length : ""),
            kind: KIND.slice, setting: "folders", keywords: "wheely settings preferences file search searched folders outside" },
          { icon: SETTING_ICON, label: "Skipped folders", trail: String(skipped.length), kind: KIND.slice,
            setting: "skipped", keywords: "wheely settings preferences file search skipped skip exclude ignore folders" },
          { icon: SETTING_ICON, label: "Forget picks", trail: String(picks), kind: KIND.slice, setting: "forget",
            keywords: "wheely settings preferences forget clear picks history remembered ranking uses" },
          { icon: "󰅐", label: "Wheely history", trail: String(picks), kind: KIND.slice, setting: "history",
            keywords: "wheely history recent picks used opened launched" }]
    .filter(function (r) { return r.setting !== "pause" || pauseKey })
}

var MANUAL_ICON = "󰋗"

// manual.md's table rows are search rows, `help` lists them, and Enter on any shows the whole
// manual. None has a key of its own, so none is counted or pinned.
function manualRows(raw) {
  var out = [{ icon: MANUAL_ICON, label: "Wheely manual", trail: "", kind: KIND.slice, manual: true,
               keywords: "wheely manual help guide keys shortcuts docs" }]
  var ls = lines(raw), section = ""
  for (var i = 0; i < ls.length; i++) {
    if (ls[i].indexOf("## ") === 0) section = ls[i].slice(3)
    var quoted = ls[i].split("|").slice(1, -1).map(function (c) { return c.trim() })
    var cells = quoted.map(function (c) { return c.replace(/`/g, "") })
    // A table's first row, over its |---| line, is its heading.
    if (cells.length !== 2 || /^-+$/.test(cells[0]) || /^\|[-|]+\|$/.test(ls[i + 1] || "")) continue
    // What is quoted in the first cell is drawn as keys; anything else there is plain words.
    var caps = (quoted[0].match(/`[^`]+`/g) || []).map(function (c) { return c.slice(1, -1) })
    out.push({ icon: MANUAL_ICON, label: cells[1], trail: cells[0] + " \u00b7 " + section, kind: KIND.manual,
               manual: true, section: section, keys: cells[0], caps: caps,
               keywords: "manual help " + section + " " + cells[0] + " " + cells[1] })
  }
  return out
}

// The manual's sections in order, in columns of about equal length: a section moves to the next
// column once more than half of it would pass that column's share.
function manualColumns(rows, count) {
  var sections = [], total = 0
  for (var i = 0; i < rows.length; i++) {
    if (!rows[i].section) continue
    var last = sections[sections.length - 1]
    if (!last || last.name !== rows[i].section) sections.push(last = { name: rows[i].section, rows: [] })
    last.rows.push(rows[i])
    total++
  }
  var columns = [[]], filled = 0
  for (var j = 0; j < sections.length; j++) {
    var n = sections[j].rows.length
    if (columns[columns.length - 1].length && columns.length < count && filled + n / 2 > total / count * columns.length)
      columns.push([])
    columns[columns.length - 1].push(sections[j])
    filled += n
  }
  return columns
}

// A key cell as combos of keycaps, a combo split at its +; plain words are one combo of none.
function combosOf(row) {
  if (!row.caps.length) return [{ plain: row.keys, caps: [] }]
  return row.caps.map(function (c) { return { plain: "", caps: /^\S+\+\S+$/.test(c) ? c.split("+") : [c] } })
}

// The user's shell.toml with one [section] key set, read as the shell reads it; other lines stay.
function withShellValue(raw, name, key, value) {
  var ls = String(raw || "").replace(/\n$/, "").split("\n")
  var line = key + " = " + value, section = "", at = -1
  for (var i = 0; i < ls.length; i++) {
    var head = ls[i].match(/^\s*\[([A-Za-z0-9_-]+)\]\s*(#.*)?$/)
    if (head) section = head[1]
    if (section !== name) continue
    if (new RegExp("^\\s*" + key + "\\s*=").test(ls[i])) { ls[i] = line; return ls.join("\n") + "\n" }
    if (ls[i].trim()) at = i + 1
  }
  if (at >= 0) { ls.splice(at, 0, line); return ls.join("\n") + "\n" }
  return (ls.join("\n").trim() ? ls.join("\n") + "\n\n" : "") + "[" + name + "]\n" + line + "\n"
}

var SHORTCUT = "SUPER + A"
var PAUSE_KEY = "CTRL + SPACE"

// A saved shortcut by the rule the Hyprland block reads it with; anything else is the default.
function shortcutIn(raw, fallback) {
  var saved = String(raw || "").split("\n")[0].trim()
  return /^[A-Z0-9_][A-Z0-9_ +]*[A-Z0-9_]$/.test(saved) && saved.indexOf(" + ") >= 0 ? saved : fallback
}

// One spelling for a combo however it was written: "SUPER SHIFT + b" is "SUPER + SHIFT + B".
function comboOf(keys) {
  var parts = String(keys || "").toUpperCase().split(/[\s+]+/).filter(Boolean)
  var key = parts.pop() || ""
  return ["SUPER", "CTRL", "ALT", "SHIFT"].filter(function (m) { return parts.indexOf(m) >= 0 })
    .concat([key]).join(" + ")
}

// What a combo already does, by its description in Omarchy's records; the wheel's own are not in the way.
function bindingAt(raw, combo) {
  var ls = lines(raw)
  for (var i = 0; i < ls.length; i++) {
    var f = ls[i].split("\t")
    var at = f[0].indexOf("→")
    if (at < 0 || comboOf(f[0].slice(0, at)) !== combo || WHEEL_BIND.test(f.slice(2).join("\t"))) continue
    return f[0].slice(at + 1).trim() || "another binding"
  }
  return ""
}

// Menu terms start words; app and window text also accepts substrings.
// Windows rank as direct hits unless a term only matched inside a word; squashed text keeps
// "wifi" matching "Wi-Fi".
function words(text) {
  var low = String(text || "").toLowerCase()
  return " " + low.replace(/[^a-z0-9]+/g, " ").trim()
       + " " + low.replace(/[^a-z0-9]+/g, "") + " "
}

function startsWord(padded, term) {
  return padded.indexOf(" " + term) !== -1
}

function wholeWord(padded, term) {
  return padded.indexOf(" " + term + " ") !== -1
}

function squash(text) {
  return String(text || "").toLowerCase().replace(/[^a-z0-9]+/g, "")
}

function search(index, query, limit, uses) {
  var q = String(query || "").trim().toLowerCase()
  if (!q) return []
  var terms = q.split(/[^a-z0-9]+/)
  var spaced = q.replace(/[^a-z0-9]+/g, " ").trim()
  var squashed = squash(q)
  var hits = []
  for (var i = 0; i < index.length; i++) {
    var e = index[i]
    // Rows are replaced when their sources refresh; normalize once on first search.
    var text = e._search || (e._search = {
      keywords: words(e.keywords), ident: e.ident ? words(e.ident) : ""
    })
    var partial = e.kind === KIND.app || e.kind === KIND.window
    var matched = true, inside = false
    for (var t = 0; t < terms.length; t++) {
      if (!terms[t]) continue
      if (startsWord(text.keywords, terms[t])) continue
      if (partial && text.keywords.indexOf(terms[t]) !== -1) { inside = true; continue }
      if (text.ident && wholeWord(text.ident, terms[t])) continue
      matched = false; break
    }
    if (!matched) continue
    if (text.squashed === undefined) text.squashed = squash(e.label)
    var rank = e.kind === KIND.window && !inside ? 0
             : text.squashed.indexOf(squashed) === 0 ? 0
             : startsWord(text.label || (text.label = words(e.label)), spaced) ? 1 : 2
    hits.push({ rank: rank, exact: text.squashed === squashed ? 0 : 1,
                uses: -(uses[keyOf(e)] || 0), len: e.label.length, entry: e })
  }
  // Among equal matches, picked rows come first, most picked first.
  hits.sort(function (a, b) {
    return a.rank - b.rank
        || a.uses - b.uses
        || a.entry.kind - b.entry.kind
        || a.exact - b.exact
        || (a.entry.recency || 0) - (b.entry.recency || 0)
        || a.len - b.len
  })
  var out = []
  for (var j = 0; j < hits.length && j < limit; j++) out.push(hits[j].entry)
  return out
}

// Leading sigils select a search source.
var MODES = { "/": "file", "=": "calc" }

function modeOf(query) {
  return MODES[String(query || "").charAt(0)] || ""
}

function termOf(query) {
  var q = String(query || "")
  return modeOf(q) ? q.slice(1) : q
}

// What `/` has always skipped, until the list is changed: a name skips that folder anywhere.
var SKIPPED = [".cache", ".git", "node_modules"]

// The scan `/` has always run over home, and a second over the folders added outside it. fd anchors
// a path only to the first folder it is given, so a skip with a slash goes to home's scan alone.
function scanCommand(roots, skipped, home) {
  var command = ["fd", "--hidden", "--max-depth", "6"]
  for (var i = 0; i < skipped.length; i++) {
    // fd reads a skip as a glob, so a name holding brackets, braces or stars is escaped to mean itself.
    var skip = String(skipped[i]).replace(/[[\]{}*?!\\]/g, "\\$&")
    if (skip.indexOf("/") < 0) command.push("--exclude", skip)
    else if (roots[0] === home && skip.indexOf("~/") === 0) command.push("--exclude", skip.slice(1) + "/")
  }
  return command.concat(["."], roots)
}

// A folder as a list writes it: from ~ when home holds it, without fd's closing slash.
function listEntry(path, home) {
  var p = String(path).replace(/\/$/, "")
  return p.indexOf(home + "/") === 0 ? "~" + p.slice(home.length) : p
}

function listedRows(name, list) {
  return list.map(function (entry) {
    return { icon: name === "folders" ? "󰉋" : "󱧸", label: entry, trail: entry.indexOf("/") < 0 ? "anywhere" : "" }
  })
}

// The subfolders a typed path starts, as a shell completes one; home and the folders holding it
// are searched already.
function subfolderRows(paths, typed, home) {
  return paths.filter(function (p) {
    return p.indexOf(typed) === 0 && (p + "/").indexOf(home + "/") !== 0 && home.indexOf(p + "/") !== 0
  }).map(function (p) { return fileRow(p + "/", home) })
}

var NO_FILES = { paths: [], lower: [] }

// fd marks directories with trailing slashes; fold case and find names once per scan.
function parseFiles(raw, into) {
  var lines = String(raw || "").split("\n")
  var paths = into ? into.paths : lines, lower = into ? into.lower : [], starts = into ? into.starts : []
  var count = into ? paths.length : 0
  for (var i = 0; i < lines.length; i++) {
    var path = lines[i].trim()
    if (!path) continue
    paths[count++] = path
    var low = path.toLowerCase()
    lower.push(low)
    // The name follows the last slash, skipping a directory's trailing one.
    starts.push(low.lastIndexOf("/", low.length - 2) + 1)
  }
  paths.length = count
  return { paths: paths, lower: lower, starts: starts }
}

function fileRow(path, home) {
  var isDir = path.charAt(path.length - 1) === "/"
  var bare = isDir ? path.slice(0, -1) : path
  var cut = bare.lastIndexOf("/")
  var dir = bare.slice(0, cut) || "/"
  return {
    icon: isDir ? "󰉋" : "󰈔",
    label: bare.slice(cut + 1),
    trail: dir.indexOf(home) === 0 ? "~" + dir.slice(home.length) : dir,
    path: path
  }
}

// A directory's own path, or the directory holding a file.
function dirOf(path) {
  var p = String(path)
  return p.charAt(p.length - 1) === "/" ? p.slice(0, -1) : p.slice(0, p.lastIndexOf("/")) || "/"
}

// From the pinned search, Files opens inside its window.
function pathPayload(path, pinned) {
  var p = String(path)
  var name = p.slice(p.lastIndexOf("/") + 1)
  var out = name ? { dir: dirOf(p), select: name } : { dir: dirOf(p) }
  if (pinned) out.pinned = true
  return JSON.stringify(out)
}

// Resumable rank buckets retain only the first limit of each tie, per scan source.
function fileRank(term, limit, home, homeFolders, uses) {
  var q = String(term || "").trim().toLowerCase(), picks = {}
  for (var key in uses) if (key.indexOf("file:") === 0) picks[key.slice(5)] = uses[key]
  return { q: q, terms: q.split(/\s+/), limit: limit, home: home, homeFolders: homeFolders,
    picks: picks, buckets: [[], [], []], picked: [[], [], []], names: {} }
}

// Append to the current query's buckets, starting after its last ranked path.
function rankFiles(rank, src, from) {
  if (!rank.q) return
  var paths = src.paths, lower = src.lower, q = rank.q, terms = rank.terms
  var starts = src.starts, homeFolders = rank.homeFolders, prefix = rank.home + "/"
  var picks = rank.picks, picked = rank.picked, buckets = rank.buckets, limit = rank.limit
  for (var i = from; i < lower.length; i++) {
    var low = lower[i]
    if (low.indexOf(terms[0]) === -1) continue
    if (homeFolders && (low.charCodeAt(low.length - 1) !== 47 || paths[i].indexOf(prefix) !== 0)) continue
    var matched = true
    for (var t = 1; t < terms.length; t++) {
      if (low.indexOf(terms[t]) === -1) { matched = false; break }
    }
    if (!matched) continue
    var start = starts[i]
    var nameEnd = low.charCodeAt(low.length - 1) === 47 ? low.length - 1 : low.length
    var at = low.indexOf(q, start)
    if (at + q.length > nameEnd) at = -1
    var r = at === start ? 0 : (at !== -1 ? 1 : 2)
    if (homeFolders && q.indexOf("/") < 0 && at === start) rank.names[paths[i].slice(start, -1)] = true
    if (picks[paths[i]]) { picked[r].push(i); continue }
    var lengths = buckets[r], ties = lengths[nameEnd - start]
    if (!ties) ties = lengths[nameEnd - start] = []
    if (ties.length < limit) ties.push(i)
  }
}

// Merge ties in source order, so late home batches still precede added folders.
function rankedFileRows(sources, limit, home) {
  var out = []
  for (var r = 0; r < 3; r++) {
    var picked = [], lengths = 0
    for (var s = 0; s < sources.length; s++) {
      var source = sources[s], rank = source.rank
      lengths = Math.max(lengths, rank.buckets[r].length)
      for (var p = 0; p < rank.picked[r].length; p++) {
        var at = rank.picked[r][p], path = source.files.paths[at]
        picked.push({ path: path, count: rank.picks[path], source: s, at: at })
      }
    }
    picked.sort(function (a, b) { return b.count - a.count || a.source - b.source || a.at - b.at })
    for (var p = 0; p < picked.length && out.length < limit; p++) out.push(fileRow(picked[p].path, home))
    for (var len = 0; len < lengths && out.length < limit; len++) {
      for (var s = 0; s < sources.length && out.length < limit; s++) {
        var source = sources[s], ties = source.rank.buckets[r][len] || []
        for (var j = 0; j < ties.length && out.length < limit; j++) out.push(fileRow(source.files.paths[ties[j]], home))
      }
    }
    if (out.length >= limit) break
  }
  return out
}

function fileRows(files, term, limit, home, homeFolders, uses) {
  var src = files || NO_FILES, rank = fileRank(term, limit, home, homeFolders, uses)
  rankFiles(rank, src, 0)
  return rankedFileRows([{ files: src, rank: rank }], limit, home)
}

// Keep each source's buckets across batches; a changed query or pick count starts a new pass.
function fileSearch(scans, query, foldersOnly, home, uses) {
  var key = JSON.stringify([String(query).trim().toLowerCase(), foldersOnly, home, uses]), names = {}
  for (var i = 0; i < scans.length; i++) {
    var scan = scans[i]
    if (scan.key !== key) {
      scan.rank = fileRank(query, 40, home, foldersOnly, foldersOnly ? null : uses)
      scan.count = 0; scan.key = key
    }
    rankFiles(scan.rank, scan.files, scan.count)
    scan.count = scan.files.paths.length
    Object.assign(names, scan.rank.names)
  }
  return Object.keys(names).sort(function (a, b) { return a.length - b.length || (a < b ? -1 : 1) })
    .slice(0, 40).map(function (name) { return { icon: "󱧸", label: name, trail: "anywhere" } })
    .concat(rankedFileRows(scans, 40, home))
}

if (typeof WorkerScript !== "undefined" && typeof WorkerScript.sendMessage === "function") {
  var scanEpoch = -1, scans = []
  WorkerScript.onMessage = function (message) {
    var reply = { epoch: message.epoch, request: message.request, rows: [] }
    try {
      if (message.epoch !== scanEpoch) {
        scanEpoch = message.epoch
        scans = [{ files: parseFiles("") }, { files: parseFiles("") }]
      }
      if (message.reset) { if (!message.rescan) gc(); return }
      for (var i = 0; i < message.chunks.length; i++) {
        var chunk = message.chunks[i]
        parseFiles(chunk.text, scans[chunk.source === "home" ? 0 : 1].files)
      }
      reply.rows = fileSearch(scans, message.query, message.foldersOnly, message.home, message.uses)
    } catch (error) { reply.error = String(error) }
    WorkerScript.sendMessage(reply)
  }
}
