const assert = require("node:assert/strict")
const { method } = require("./qml.js")
const { wheelSource, binding, M } = require("./wheel-source.js")

const later = [], sent = []
const root = { fileBusy: false, fileSearchKey: "file:alpha", opened: true, windowed: false,
  filesReady: true, fileQueue: [], scanEpoch: 2, fileRequest: 5, fileResultRequest: 4,
  listing: "", term: "alpha", home: "/home/test", uses: {}, fileResults: [{ path: "/old" }] }
const Qt = { callLater: fn => { if (!later.includes(fn)) later.push(fn) } }
const fileWorker = { ready: true, sendMessage: message => sent.push(message) }
root.sendFiles = method(wheelSource, "sendFiles", { root, fileWorker })
const receive = new Function("root", "Qt", "return " + wheelSource.match(/onMessage: (message => \{[^]*?^    })/m)[1])(root, Qt)
const change = new Function("root", "Qt", wheelSource.match(/onFileSearchKeyChanged: \{([^]*?)^  }/m)[1]).bind(null, root, Qt)
root.sendFiles(); root.sendFiles()
assert.equal(sent.length, 1, "more than one job in flight")
root.term = "beta"; change(); root.term = "gamma"; change()
assert.deepEqual(root.fileResults, [{ path: "/old" }], "typing blanked visible results")
while (later.length) later.shift()()
assert.equal(sent.length, 1, "typing sent a job while busy")
receive({ epoch: 2, request: 5, rows: [{ path: "/alpha" }] })
assert.deepEqual(root.fileResults, [{ path: "/old" }], "an obsolete reply replaced rows")
while (later.length) later.shift()()
assert.equal(sent.length, 2)
assert.equal(sent[1].query, "gamma")
receive({ epoch: 1, request: 7, rows: [] })
receive({ epoch: 2, reset: true })
assert.equal(root.fileBusy, true, "old epoch or reset reply unlocked a current job")
receive({ epoch: 2, request: 7, rows: [{ path: "/gamma" }] })
assert.equal(root.fileBusy, false)
assert.equal(root.fileResultRequest, 7)
assert.deepEqual(root.fileResults, [{ path: "/gamma" }])
assert.equal(binding("fileSearchKey", { root: { listing: "", mode: "file", term: "  GAMMA " } }), "file:gamma")
assert.equal(binding("fileSearchKey", { root: { listing: "skipped", query: " TARGET " } }), "skip:target")

// Pending rows cannot be launched, copied or opened in a terminal.
root.filePending = true
root.results = [{ path: "/old" }]; root.resultIndex = 0; root.searching = true
root.countUse = root.dismiss = root.copy = () => assert.fail("acted on stale results")
method(wheelSource, "run", { root, unmap: { running: false } })(root.results[0])
assert.equal(method(wheelSource, "terminal", { root })(), false)
assert.equal(method(wheelSource, "takePath", { root })(), false)

// GlobalShortcut press and release route through the same production handlers.
const shortcuts = wheelSource.match(/  GlobalShortcut \{([^]*?)^  }/m)[1], calls = []
const shortcutRoot = { pluginId: "xpo.wheel", shell: { toggle: (...args) => calls.push(args) },
  commit: () => calls.push("release") }
for (const event of ["Pressed", "Released"])
  new Function("root", shortcuts.match(new RegExp("on" + event + ": (.*)"))[1])(shortcutRoot)
assert.deepEqual(calls, [["xpo.wheel", "{}"], "release"])
console.log("ok: one job in flight, stale replies, retained rows, guarded picks and shortcut handlers")
