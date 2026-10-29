const assert = require("node:assert/strict")
const fs = require("node:fs")
const path = require("node:path")
const read = name => fs.readFileSync(path.join(__dirname, "../plugins/xpo.wheel", name), "utf8")
const wheel = read("Wheel.qml")

// Disc illumination is continuous in both directions and clears at rest.
const sweepRoot = { arcSpread: 17, arcHead: -90, arcDrag: 0, spinFade: 1 }
const sweepAt = new Function("root", "deg", wheel.match(/function sweepAt\(deg\) \{([^]*?)\n  }/)[1])
const sweep = (deg, drag) => { sweepRoot.arcDrag = drag; return sweepAt(sweepRoot, deg) }
// -90 is the head itself.
for (const deg of [-90, -50, 0, 90, 180])
  assert.equal(sweep(deg, 0), 0, "a ring at rest lights " + deg)
assert.ok(sweep(-90, 40) > 0.9, "a moving head still lights what it is on")
assert.ok(sweep(-90, 8) < sweep(-90, 40), "and a slower ring lights it less")
assert.equal(sweep(90, 40), 0, "nothing lights where the streak is not")
// Crossing either edge or the back of a long trail must not flash a disc.
for (const drag of [40, -40, 300, -300]) {
  let previous = sweep(-270, drag)
  for (let deg = -269.9; deg <= 90; deg += 0.1) {
    const light = sweep(deg, drag)
    assert.ok(light >= 0 && light <= 1, "trail brightness stays bounded")
    assert.ok(Math.abs(light - previous) < 0.02,
      `trail jumps at ${deg.toFixed(1)} degrees with drag ${drag}`)
    assert.ok(Math.abs(light - sweep(deg + 360, drag)) < 1e-10,
      "trail stays continuous across laps")
    assert.ok(Math.abs(light - sweep(-180 - deg, -drag)) < 1e-10,
      "both spin directions share the same lighting")
    previous = light
  }
}
console.log("ok: the comet lights what it crosses and gives it back at rest")
sweepRoot.spinFade = 0
assert.equal(sweep(-90, 300), 0, "navigation triggered the spin lighting")

// Even at full speed, the visible comet leaves at least a third of the ring quiet
// and keeps its leading edge beside the head in either direction.
{
  const expr = name => new Function("root", "return " + wheel.match(
    new RegExp("readonly property real " + name + ": (.+)"))[1])
  const span = expr("arcSpan"), from = expr("arcFrom")
  for (const count of [8, 9, 12, 24]) {
    for (const drag of [-300, -40, 0, 40, 300]) {
      const state = { arcSpread: 360 / count / 2 * 0.85, arcDrag: drag, arcHead: 1440, spinFade: 1 }
      state.arcSpan = span(state)
      assert.ok(state.arcSpan <= 240, "fast comet closes into a circle")
      assert.ok(state.arcSpan >= state.arcSpread * 2, "selection bracket shrank")
      const tip = drag >= 0 ? from(state) + state.arcSpan : from(state)
      assert.ok(Math.abs(tip - (state.arcHead + (drag >= 0 ? 1 : -1) * state.arcSpread)) < 1e-9,
        "shortening the trail moved its head")
      state.spinFade = 0
      assert.equal(span(state), state.arcSpread * 2, "navigation widened the selection into a spin trail")
    }
  }
}
console.log("ok: the comet retains a third-ring gap and follows its head")

// The shader's visible tip follows slice motion across effect start and release.
{
  const source = read("RingTrack.qml")
  const binding = name => new Function("root", "return " + source.match(
    new RegExp("readonly property real " + name + ": (.+)"))[1])
  const from = binding("arcFrom"), span = binding("arcSpan")
  const expression = name => new Function("root", "return " + wheel.match(
    new RegExp("readonly property real " + name + ": (.+)"))[1])
  const wheelFrom = expression("arcFrom"), wheelSpan = expression("arcSpan")
  for (const direction of [-1, 1]) {
    const state = { arcHead: -90, arcDrag: direction * 300, arcSpread: 17, spinFade: 0 }
    let previous = null
    let previousSpan = null
    for (const fade of [0, 0, 0.5, 1, 1, 0.5, 0]) {
      state.spinFade = fade
      state.arcSpan = wheelSpan(state)
      state.arcFrom = wheelFrom(state)
      const tip = (from({ wheel: state }) + (direction > 0 ? span({ wheel: state }) : 0)) * 180 / Math.PI
      assert.ok(Math.abs(tip - (state.arcHead + direction * state.arcSpread)) < 1e-8,
        "effect handoff moved the visible tip away from selection")
      if (previous !== null) assert.ok(Math.abs(tip - previous - direction * 45) < 1e-8,
        "effect handoff changed the visible speed")
      if (previousSpan !== null) assert.ok(Math.abs(state.arcSpan - previousSpan) <= 300 * 0.5 + 1e-9,
        "effect handoff snapped the trail length")
      previous = tip
      previousSpan = state.arcSpan
      state.arcHead += direction * 45
    }
  }
}
console.log("ok: starting and ending effects ease the trail without moving its tip")
