const assert = require("node:assert/strict")
const { M } = require("./wheel-source.js")
const { worker } = require("./wheel-worker-fixture.js")

const w = worker(), all = { home: [], folders: [] }
const message = { epoch: 0, request: 0, query: "ta", home: "/home/test", skipped: false, uses: {}, chunks: [] }
function expected() {
  const files = M.parseFiles(all.home.concat(all.folders).join("\n"))
  const q = message.query.trim().toLowerCase(), terms = q.split(/\s+/)
  // Independent full-sort oracle for matching, rank, picks, name length and stable source ties.
  const ranked = files.paths.map((path, at) => {
    const low = path.toLowerCase(), name = low.replace(/\/$/, "").split("/").at(-1)
    return { path, at, name, matches: q && terms.every(term => low.includes(term))
      && (!message.skipped || path.startsWith(message.home + "/") && path.endsWith("/")),
      rank: name.startsWith(q) ? 0 : name.includes(q) ? 1 : 2,
      pick: message.skipped ? 0 : message.uses["file:" + path] || 0 }
  }).filter(row => row.matches).sort((a, b) => a.rank - b.rank || b.pick - a.pick
    || (a.pick ? 0 : a.name.length - b.name.length) || a.at - b.at)
  return (message.skipped ? M.nameRows(files, message.query, 40, message.home) : []).concat(
    ranked.slice(0, 40).map(row => M.fileRow(row.path, message.home)))
}
// Interleaved batches: late home ties lead folders, picked ties retain source order, and
// query/pick/mode changes must agree with a single full pass over home followed by folders.
for (let batch = 0; batch < 300; batch++) {
  const source = batch % 3 ? "folders" : "home", prefix = source === "home" ? message.home : "/mnt"
  const paths = Array.from({ length: 31 }, (_, i) => prefix + "/" + batch + "/"
    + ["target/", "targets/", "ta.txt", "star.txt", "café/", "TARGET.txt", "ta r.txt"][i % 7])
  all[source].push(...paths)
  message.chunks = [{ source, text: paths.join("\n") }]
  if (batch % 17 === 0) message.uses["file:" + paths[2]] = batch + 1
  message.skipped = batch % 30 >= 15
  message.query = ["ta", "tar", "target", "t", "ta r", "/", "ca", "  CAFÉ ", "nomatch"][Math.floor(batch / 7) % 9]
  message.request++
  assert.deepEqual(w.finish(message), expected(), "batch " + batch)
}

// After the first pass, an append must rank only the appended paths. A narrower query
// should examine the match set; a wider query still examines the full index.
let visited = 0
const rankFiles = w.context.rankFiles
w.context.rankFiles = (...args) => { visited += args[3] - args[2]; return rankFiles(...args) }
message.skipped = false; message.query = "café"; message.chunks = []
w.finish(message); visited = 0
message.chunks = [{ source: "home", text: "/home/test/caféteria" }]
w.finish(message)
assert.equal(visited, 1, "a batch re-ranked older paths")
visited = 0; message.chunks = []; message.query = "cafét"
w.finish(message)
assert.ok(visited < 2000, "narrowing discarded the match set")
visited = 0; message.query = "t"
w.finish(message)
assert.equal(visited, 9301, "broadening missed paths outside the old match set")

// An obsolete search yields in bounded slices, so the next message can supersede it.
message.query = "/"; message.request++
message.chunks = [{ source: "home", text: Array(50000).fill("/home/test/extra").join("\n") }]
visited = 0
const partial = w.send(message)
assert.equal(partial.more, true)
assert.ok(visited <= 32768)
message.chunks = []
message.query = "caféteria"; message.request++
assert.deepEqual(w.finish(message).map(e => e.path), ["/home/test/caféteria"])

// Reset acknowledges without publishing old rows; errors also always produce a reply.
assert.equal(w.send({ epoch: 1, reset: true }).reset, true)
assert.deepEqual(w.finish({ ...message, epoch: 1, chunks: [] }), [])
w.context.rankFiles = () => { throw Error("test ranking failure") }
assert.match(w.send({ ...message, epoch: 1, query: "changed" }).error, /test ranking failure/)
console.log("ok: worker batch parity, incremental ranking, query interruption, reset and error replies")
