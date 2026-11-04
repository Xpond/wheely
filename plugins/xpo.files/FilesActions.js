.pragma library

// The right-click menu as data: what the selection is decides the rows it offers, and each row says
// what it runs. Pure, so tests read the same table the menu draws.

var SEP = { sep: true }

function row(id, label, hint, run, extra) {
  return Object.assign({ id: id, label: label, hint: hint || "", run: run }, extra)
}

// A submenu with nothing in it is not offered.
function sub(id, label, rows) {
  rows = tidy(rows)
  return rows.length ? { id: id, label: label, sub: rows } : null
}

// Drops the rows that do not apply, and the separators they leave leading, trailing or doubled.
function tidy(rows) {
  var out = []
  rows.forEach(function (r) {
    if (r && !(r.sep && (!out.length || out[out.length - 1].sep))) out.push(r)
  })
  while (out.length && out[out.length - 1].sep) out.pop()
  return out
}

// What Extract here unpacks: the name less its archive suffix, or "" for anything else.
function archiveStem(name) {
  var m = /^(.+?)\.(tar\.(gz|bz2|xz|zst)|tgz|tbz2|txz|tzst|tar|zip|7z|rar|iso)$/i.exec(String(name))
  return m ? m[1] : ""
}

// A shebang says so; the extensions catch a script whose first line has not been read.
function isScript(name, text) {
  return /\.(sh|bash|zsh|fish|py|rb|pl)$/i.test(String(name)) || /^#!/.test(String(text || ""))
}

// Writes test their destination first, as FilesOps.guarded does: 17 when the name is taken.
var TAKEN = 'if [ -e "$2" ] || [ -L "$2" ]; then exit 17; fi; '

// Archives entries of one folder from inside it, so the archive holds their names rather than their
// paths. A failed archive leaves nothing behind.
function compressCommand(dir, archive, names) {
  var make = /\.zip$/.test(archive) ? 'zip -qry "$a" -- "$@"' : 'bsdtar -acf "$a" -- "$@"'
  return ["sh", "-c", 'cd -- "$1" || exit 1; ' + TAKEN + 'a=$2; shift 2; ' + make + ' || { rm -f -- "$a"; exit 1; }',
          "files", dir, archive].concat(names)
}

// Unpacks into a folder named after the archive; one holding a single folder of that same name gives
// that folder rather than nesting it twice. Unpacked aside first, so a failure leaves nothing.
function extractCommand(path, target) {
  return ["sh", "-c", TAKEN + 't="${2%/*}/.extract-$$"; mkdir -- "$t" || exit 1; ' +
    'bsdtar -xf "$1" -C "$t" || { rm -rf -- "$t"; exit 1; }; n=${2##*/}; ' +
    'if [ "$(ls -A -- "$t")" = "$n" ] && [ -d "$t/$n" ] && [ ! -L "$t/$n" ]; ' +
    'then mv -T -- "$t/$n" "$2" && rmdir -- "$t"; else mv -T -- "$t" "$2"; fi',
    "files", path, target]
}

// Where omarchy-transcode writes: beside the original, its stem marked with the size.
function convertTarget(path, format, size) {
  return path.replace(/\.[^.\/]*$/, "") + "-" + size + "." + format
}

// The files themselves as a text/uri-list: what an app takes as attachments when they are pasted.
function clipCommand(urls) {
  return ["sh", "-c", 'printf "%s\\n" "$@" | wl-copy --type text/uri-list', "files"].concat(urls)
}

// As Omarchy's own launcher: a terminal app through its TUI launcher, the rest through gtk-launch.
function openWithCommand(app, path) {
  return app.terminal ? ["omarchy-launch-tui"].concat(app.command, [path])
                      : ["uwsm-app", "--", "gtk-launch", app.id + ".desktop", path]
}

// A script runs in its own folder, and its window stays until Enter so its output can be read.
function runCommand(path) {
  return ["omarchy-launch-tui", "bash", "-c",
          'cd -- "${1%/*}" && "$1"; printf "\\n[exit %s] Enter closes this window" "$?"; read -r _',
          "run", path]
}

// One process as a row's menu opens: whether it is executable, gio's apps for its type, and the
// devices Taildrop can reach.
var PROBE = '[ -f "$1" ] && [ -x "$1" ] && echo executable; ' +
  't=$(gio info -a standard::content-type "$1" 2>/dev/null | sed -n "s/^ *standard::content-type: //p"); ' +
  '[ -n "$t" ] && LC_ALL=C gio mime "$t" 2>/dev/null; echo peers; ' +
  'command -v tailscale >/dev/null && timeout 2 tailscale file cp --targets 2>/dev/null; exit 0'

// Apps by desktop id, the default first. A Taildrop target is an address and a name, with a third
// field only when it is offline, and only those online can take a file.
function readProbe(text) {
  var out = { executable: false, apps: [], preferred: "", peers: [] }, peers = false
  String(text || "").split("\n").forEach(function (line) {
    var m
    if (line === "executable") out.executable = true
    else if (line === "peers") peers = true
    else if (peers) { var f = line.split("\t"); if (f.length === 2 && f[1]) out.peers.push(f[1]) }
    else if (/^Default application/.test(line)) out.preferred = (line.match(/: (.+)\.desktop$/) || ["", ""])[1]
    else if ((m = line.match(/^\t(.+)\.desktop$/)) && out.apps.indexOf(m[1]) < 0) out.apps.push(m[1])
  })
  if (out.preferred) out.apps = [out.preferred].concat(out.apps.filter(function (a) { return a !== out.preferred }))
  return out
}

var CONVERSIONS = {
  image: [["jpg", "high"], ["jpg", "medium"], ["jpg", "low"], ["png", "high"], ["png", "medium"], ["png", "low"]],
  video: [["mp4", "4k"], ["mp4", "1080p"], ["mp4", "720p"], ["gif", "4k"], ["gif", "1080p"], ["gif", "720p"]]
}

// What is held, placed in this folder or into a folder row.
function pasteRow(c, into) {
  var held = (c.held.move ? "Move " : "Copy ") + c.held.name
  return into ? row("into", held + " into " + into.name, "", function () { c.ops.paste(into.path) })
              : row("paste", held + " here", "ctrl+v", function () { c.ops.paste() })
}

// The menu for one entry or for the marks, or for the folder itself when there is neither. Marks
// get only the verbs that take many: the rest name one file, or need one to know what it is.
function tree(c) {
  var e = c.entry, p = c.panel, o = c.ops
  if (!e && !c.many) return folderRows(c)
  if (e && e.missing) return [row("open", "Show changes", "enter", function () { o.activate(e) }),
                              row("path", "Copy path", "ctrl+y", function () { o.copyPath([e]) })]
  var list = c.many || [e], named = o.label(list), one = c.many ? null : e
  // One entry's own folder, which a folder's preview shows rather than the list; the marks' is the
  // folder listed, whose typed path keeps its trailing slash.
  var here = String(c.dir).replace(/(.)\/+$/, "$1")
  var dir = one ? e.path.slice(0, e.path.lastIndexOf("/")) || "/" : here
  var land = dir === here
  var paths = list.map(function (t) { return t.path }), files = list.every(function (t) { return !t.isDir })
  // A root's row stands for the root itself: it cannot be held, renamed, archived or trashed.
  var own = !one || !one.shortcut, file = !!one && !one.isDir, media = file && (c.image || c.video)
  var stem = file ? archiveStem(e.name) : ""
  return tidy([
    c.many && row("count", named, "", null, { off: true }),
    one && row("open", "Open", "enter", function () { o.activate(e) }),
    one && sub("with", "Open with", c.apps === null ? [row("looking", "looking…", "", null, { off: true })]
      : c.apps.map(function (a) {
          return row("with:" + a.id, a.name, a.id === c.preferred ? "default" : "",
                     function () { o.launch(openWithCommand(a, e.path)) }) })),
    file && c.editable && row("edit", "Edit", "ctrl+e", function () { p.edit() }),
    file && c.script && c.executable && row("run", "Run in a terminal", "", function () { o.launch(runCommand(e.path)) }),
    one && e.isDir && row("terminal", "Open in a terminal", "", function () { o.terminal(e.path) }),
    one && row("nautilus", "Show in Nautilus", "", function () { o.launch(["uwsm-app", "--", "nautilus", "--select", e.path]) }),
    SEP,
    // Taildrop is a row for each device online, not a menu of its own: no menu opens two deep, where
    // the menus before it leave it no room.
    sub("share", "Share", [
      row("localsend", "LocalSend…", "", function () { o.launch(["omarchy-menu-share", "file"].concat(paths)) })
    ].concat((files ? c.peers : []).map(function (name) {
      return row("to:" + name, "Taildrop to " + name, "", function () {
        o.detach(["omarchy-tailscale-send", name].concat(paths), "sending " + named + " to " + name) }) }), [
      row("clip", "Copy to clipboard", "", function () { o.run(clipCommand(c.urls), { done: "copied " + named, fail: "copy failed" }) }),
      c.image && row("pixels", "Copy image", "", function () {
        o.run(["sh", "-c", 'exec wl-copy --type "$(file -b --mime-type -- "$1")" < "$1"', "files", e.path],
              { done: "copied the image", fail: "copy failed" }) })
    ])),
    media && sub("convert", "Convert for sharing", CONVERSIONS[c.image ? "image" : "video"].map(function (f) {
      return row("as:" + f.join("-"), f[0].toUpperCase() + " · " + f[1], "", function () {
        var out = convertTarget(e.path, f[0], f[1])
        o.run(["sh", "-c", TAKEN, "files", e.path, out],
              { name: out.slice(out.lastIndexOf("/") + 1), done: "converting " + e.name, fail: "convert failed",
                then: ["omarchy-transcode", e.path, f[0], f[1]] }) }) })),
    media && row("wallpaper", "Set as wallpaper", "", function () {
      o.run(["omarchy-theme-bg-set", e.path], { done: "wallpaper set", fail: "could not set the wallpaper" }) }),
    stem && row("extract", "Extract here", "", function () {
      o.run(extractCommand(e.path, dir + "/" + stem), { name: stem, land: land, done: "extracted " + e.name, fail: "extract failed" }) }),
    // Many go into one archive, named after their folder.
    own && sub("compress", "Compress", [".zip", ".tar.zst"].map(function (ext) {
      var name = (one ? e.name : dir.slice(dir.lastIndexOf("/") + 1)) + ext
      return row("pack" + ext, name, "", function () {
        o.run(compressCommand(dir, dir + "/" + name, list.map(function (t) { return t.name })),
              { name: name, land: land, done: "compressed " + named, fail: "compress failed" }) }) })),
    file && c.script && !c.executable && row("exec", "Make executable", "", function () {
      o.run(["chmod", "+x", "--", e.path], { done: "made " + e.name + " executable", fail: "could not make it executable" }) }),
    SEP,
    own && row("cut", "Cut", "ctrl+x", function () { o.hold(list, true) }),
    own && row("copy", "Copy", "ctrl+c", function () { o.hold(list, false) }),
    c.held && one && e.isDir && !c.held.items.some(function (i) { return i.path === e.path }) && pasteRow(c, e),
    c.held && pasteRow(c),
    c.many && row("unmark", "Unmark all", "esc", function () { p.unmarkAll() }),
    one && own && row("duplicate", "Duplicate…", "", function () { p.beginCopyName("copy", e) }),
    one && own && row("rename", "Rename…", "f2", function () { p.beginRename(e) }),
    one && own && row("link", "Make link…", "", function () { p.beginCopyName("link", e) }),
    SEP,
    row("path", c.many ? "Copy paths" : "Copy path", "ctrl+y", function () { o.copyPath(list) }),
    // Asked twice, as Del is: the first pick arms it and keeps the menu open, the second trashes.
    own && row("trash", c.doomed ? "Again to trash " + named : c.many ? "Trash " + named : "Trash", "del",
               function () { o.remove(list); return !!o.doomed }, { danger: true }),
    SEP,
    sub("here", "Current folder", folderRows(c))
  ])
}

function folderRows(c) {
  var p = c.panel, o = c.ops
  return tidy([
    row("new", "New file or folder…", "ctrl+shift+n", function () { p.beginNew() }),
    c.held && pasteRow(c),
    row("terminal", "Open in a terminal", "ctrl+enter", function () { o.terminal(c.dir) }),
    row("nautilus", "Show in Nautilus", "", function () { o.launch(["uwsm-app", "--", "nautilus", "--new-window", c.dir]) }),
    SEP,
    row("hidden", c.showHidden ? "Hide hidden files" : "Show hidden files", "ctrl+h", function () { p.showHidden = !c.showHidden })
  ].concat([["name", "Sort by name"], ["date", "Sort newest first"], ["size", "Sort largest first"]].map(function (s) {
    return row("by:" + s[0], s[1], c.order === s[0] ? "•" : "", function () { p.order = s[0]; p.index = 0 }) }), [
    row("window", c.popped ? "Back to the overlay" : "Pop out to a window", "ctrl+t", function () { p.popOut() })
  ]))
}
