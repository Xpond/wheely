// Load the actual worker, including its production import and message handler.
const vm = require("node:vm")
const { read } = require("./qml.js")

function worker() {
  let reply
  const context = vm.createContext({ gc() {}, WorkerScript: { sendMessage: value => { reply = value } } })
  context.Qt = { include: file => vm.runInContext(read("plugins/xpo.wheel/" + file), context) }
  vm.runInContext(read("plugins/xpo.wheel/FileWorker.js"), context)
  return {
    context,
    send(message) { context.WorkerScript.onMessage(message); return JSON.parse(JSON.stringify(reply)) },
    finish(message) {
      let result = this.send(message), rounds = 1
      while (result.more) {
        if (++rounds > 1000) throw Error("worker did not finish")
        result = this.send({ ...message, chunks: [] })
      }
      if (result.error) throw Error(result.error)
      return result.rows
    }
  }
}

function fileSearch(files, query, skipped, home, uses = {}) {
  return worker().finish({ epoch: 0, request: 0, chunks: [{ source: "home", text: files.paths.join("\n") }],
    query, skipped, home, uses })
}

module.exports = { worker, fileSearch }
