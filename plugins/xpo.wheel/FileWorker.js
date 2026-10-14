Qt.include("MenuIndex.js")

var epoch = -1, scans, pending, searchKey, warming

function resetScan() {
  scans = [0, 1].map(function () {
    return { files: parseFiles(""), rank: null, cursor: 0, candidates: null, complete: false }
  })
  pending = []
  searchKey = ""
  warming = false
}

function searchFiles(message) {
  if (message.epoch !== epoch || message.reset) { epoch = message.epoch; resetScan() }
  if (message.reset) { gc(); return { reset: true } }
  var q = String(message.query || "").trim().toLowerCase()
  var key = JSON.stringify([q, message.skipped, message.home, message.uses])
  pending = pending.concat(message.chunks)
  if (key !== searchKey) {
    for (var s = 0; s < scans.length; s++) {
      var scan = scans[s], old = scan.rank
      // Every match of a longer prefix was also a match of the old query.
      scan.candidates = old && scan.complete && old.q && q.indexOf(old.q) === 0
        && old.homeFolders === message.skipped && old.home === message.home ? old.matches : null
      scan.rank = fileRank(q, 40, message.home, message.skipped, message.skipped ? null : message.uses)
      scan.cursor = 0
      scan.complete = false
    }
    warming = !!searchKey
    searchKey = key
  }
  // Reply between slices: the UI can replace an obsolete query without waiting for a full pass.
  var budget = 32768
  while (budget > 0) {
    var scan = scans.filter(function (s) { return !s.complete })[0]
    if (scan) {
      var count = scan.candidates ? scan.candidates.length : scan.files.paths.length
      var end = Math.min(count, scan.cursor + budget)
      rankFiles(scan.rank, scan.files, scan.cursor, end, scan.candidates)
      budget -= end - scan.cursor
      scan.cursor = end
      scan.complete = end === count
    } else {
      warming = false
      if (!pending.length) break
      var chunk = pending.shift()
      var scan = scans[chunk.source === "home" ? 0 : 1]
      scan.cursor = scan.files.paths.length
      scan.candidates = null
      parseFiles(chunk.text, scan.files)
      scan.complete = false
    }
  }
  var more = pending.length > 0 || scans.some(function (s) { return !s.complete })
  if (!more) warming = false
  var reply = { more: more }
  if (!warming) {
    var names = Object.assign({}, scans[0].rank.names, scans[1].rank.names)
    reply.rows = Object.keys(names).sort(function (a, b) { return a.length - b.length || (a < b ? -1 : 1) })
      .slice(0, 40).map(function (name) { return { icon: "󱧸", label: name, trail: "anywhere" } })
      .concat(rankedFileRows(scans, 40, message.home))
  }
  return reply
}

WorkerScript.onMessage = function (message) {
  var reply
  try { reply = searchFiles(message) }
  catch (error) { reply = { rows: [], error: String(error) } }
  reply.epoch = message.epoch
  reply.request = message.request
  WorkerScript.sendMessage(reply)
}
