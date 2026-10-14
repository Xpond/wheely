const assert = require("node:assert/strict")
const { read, method, keymap } = require("./qml.js")

let toggles = 0
const panel = { editing: false, naming: "", showsVideo: true, listShown: true,
  filter: "movie", index: 7, pending: "movie.mp4" }
const key = keymap("plugins/xpo.files/FilesKeys.js", panel, { doomed: "" }, {
  toggleVideo() { toggles++ }
})
for (const filter of ["", "movie", "~/Videos/movie"]) {
  panel.filter = filter
  for (const listShown of [true, false]) {
    panel.listShown = listShown
    assert.equal(key("Key_Space", 0, " ").accepted, true)
    assert.equal(panel.index, 7, "Space must not move the selection")
    assert.equal(panel.filter, filter, "Space must not change the filter")
    assert.equal(panel.pending, "movie.mp4")
  }
}
assert.equal(toggles, 6)
assert.equal(key("Key_Space", 0, " ", true).accepted, true)
assert.equal(toggles, 6, "holding Space must not repeatedly toggle playback")
key("Key_Space", 1 << 25, " ")
assert.equal(panel.filter, "~/Videos/movie ", "Shift+Space must type a literal space")
assert.equal(toggles, 6)

panel.showsVideo = false; panel.filter = "notes"; panel.index = 7
key("Key_Space", 0, " ")
assert.equal(panel.filter, "notes ", "Space still types into a non-video filter")
assert.equal(toggles, 6)
panel.showsVideo = true; panel.editing = true
assert.equal(key("Key_Space", 0, " ").accepted, false, "the editor must receive Space")
panel.editing = false; panel.naming = "rename"
panel.renameKey = event => { assert.equal(event.text, " ") }
assert.equal(key("Key_Space", 0, " ").accepted, true)
assert.equal(toggles, 6, "renaming must not control playback")

const video = { item: null }
const toggleVideo = method(read("plugins/xpo.files/FilesPreview.qml"), "toggleVideo", { video })
toggleVideo()
video.item = { toggle() { toggles++ } }
toggleVideo()
assert.equal(toggles, 7)
console.log("ok: Space toggles video without changing selection or filter; text entry and key repeat stay safe")
