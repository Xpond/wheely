// Cancel a running extract, compress and paste with the production commands, and read a job's gauge.
// Stubs stand in for bsdtar, zip and cp: each writes part of its output and then hangs, as a big job
// does, so the cancel lands mid-write.
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { spawn, spawnSync } = require("node:child_process")
const { read, library, method, keymap } = require("./qml.js")
const A = library("plugins/xpo.files/FilesActions.js")
const opsSource = read("plugins/xpo.files/FilesOps.qml")
const base = fs.mkdtempSync(path.join(os.tmpdir(), "files-cancel-"))
const at = (...p) => path.join(base, ...p)
const pause = ms => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms)
function until(ok, what) {
  for (let i = 0; i < 200; i++) { if (ok()) return; pause(25) }
  throw new Error("timed out waiting for " + what)
}
const scope = { root: {}, filer: {}, Quickshell: { execDetached: argv => spawnSync(argv[0], argv.slice(1)) } }
const cancel = method(opsSource, "cancel", scope)
const gaugeCommand = method(opsSource, "gaugeCommand", {})
const env = { ...process.env, PATH: at("bin") + ":" + process.env.PATH }

// Runs a job as Files does, cancels it once it is under way, and gives its exit status.
function cancelled(command, underway, gauged) {
  const status = at("status")
  fs.rmSync(status, { force: true }); fs.rmSync(status + ".pid", { force: true })
  spawn("sh", ["-c", '"$@" & echo $! > "$0.pid"; wait $!; echo $? > "$0"', status, ...command], { env, stdio: "ignore" })
  until(() => fs.existsSync(status + ".pid") && underway(), "the job to start")
  const pid = +fs.readFileSync(status + ".pid", "utf8")
  if (gauged) gauged(pid)
  Object.assign(scope.root, { busy: true, cancelling: false }); scope.filer.processId = pid
  cancel()
  until(() => fs.existsSync(status), "the job to stop")
  return +fs.readFileSync(status, "utf8")
}

try {
  fs.mkdirSync(at("bin"))
  const stub = (name, body) => fs.writeFileSync(at("bin", name), "#!/bin/sh\n" + body + "\nexec sleep 30\n", { mode: 0o755 })
  stub("bsdtar", 'mkdir "$4/partial" && cat "$2" > "$4/partial/copy"')
  stub("zip", 'printf partial > "$2"')
  stub("cp", 'cat "$3" > "$4"')

  // Extract: the scratch folder goes, nothing lands, and the gauge has read the whole archive.
  fs.mkdirSync(at("x"))
  const archive = at("x", "big.zip")
  fs.writeFileSync(archive, Buffer.alloc(3000000, 1))
  const scratch = () => fs.readdirSync(at("x")).find(n => n.startsWith(".extract-"))
  let line = ""
  assert.notEqual(cancelled(A.extractCommand(archive, at("x", "big")), () => scratch() && fs.existsSync(at("x", scratch(), "partial", "copy")) && fs.statSync(at("x", scratch(), "partial", "copy")).size === 3000000,
    pid => { line = String(spawnSync(gaugeCommand(pid, [archive])[0], gaugeCommand(pid, [archive]).slice(1), { timeout: 1500 }).stdout).split("\n")[0] }), 0)
  assert.deepEqual(fs.readdirSync(at("x")), ["big.zip"], "a cancelled extract left files behind")
  const [done, total] = line.split(" ").map(Number)
  assert.equal(total, 3000000)
  assert.ok(done >= total && done < total * 1.05, "the gauge read " + line)

  // Compress: the half-written archive goes.
  fs.mkdirSync(at("c")); fs.writeFileSync(at("c", "a.txt"), "a")
  assert.notEqual(cancelled(A.compressCommand(at("c"), at("c", "c.zip"), ["a.txt"]), () => fs.existsSync(at("c", "c.zip"))), 0)
  assert.deepEqual(fs.readdirSync(at("c")), ["a.txt"], "a cancelled compress left its archive")

  // Copy, and a move to another filesystem (stat says so): the copy being made goes, the sources stay,
  // and the next is never started.
  fs.mkdirSync(at("from")); fs.mkdirSync(at("to"))
  for (const n of ["one", "two"]) fs.writeFileSync(at("from", n), n)
  const pasteCommand = method(opsSource, "pasteCommand", {})
  for (const move of [false, true]) {
    if (move) fs.writeFileSync(at("bin", "stat"), "#!/bin/sh\necho $$\n", { mode: 0o755 })
    const paste = pasteCommand(move, at("to"), [at("from", "one"), at("from", "two")])
    assert.equal(cancelled(paste, () => fs.existsSync(at("to", "one"))), 130)
    assert.deepEqual(fs.readdirSync(at("to")), [], "a cancelled paste left a partial copy or went on to the next")
    assert.deepEqual(fs.readdirSync(at("from")).sort(), ["one", "two"], "a cancelled paste lost a source")
  }

  // Ctrl+K cancels; it is no one else's key outside naming and editing.
  let asked = 0
  const press = keymap("plugins/xpo.files/FilesKeys.js", { editing: false, naming: "", menu: null }, { cancel() { asked++ } }, {})
  assert.ok(press("Key_K", 1 << 26).accepted)
  assert.equal(asked, 1)
} finally {
  fs.rmSync(base, { recursive: true, force: true })
}
console.log("ok: cancelled extract, compress, copy and move leave nothing behind; the gauge reads what a job has read")
