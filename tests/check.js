// Logic and lifecycle regressions. Run: node tests/check.js
// Every suite runs even when an earlier one fails, and the run fails if any did. Four need this
// machine's tools: wheel-settings.js the installed Omarchy shell, wheel-folders.js fd,
// shell-panels.js the omarchy CLI, scene.js Qt's qsb.

const suites = [
  "./files-index.js",
  "./files-git.js",
  "./files-order.js",
  "./wheel-menu.js",
  "./wheel-search.js",
  "./wheel-binds.js",
  "./wheel-calc.js",
  "./wheel-conditions.js",
  "./files-navigation.js",
  "./wheel-input.js",
  "./wheel-navigation.js",
  "./wheel-pointer.js",
  "./wheel-settings.js",
  "./wheel-manual.js",
  "./wheel-ring.js",
  "./wheel-folders.js",
  "./wheel-files.js",
  "./shell-panels.js",

  "./wheel-actions.js",
  "./wheel-close.js",
  "./files-ops.js",
  "./files-menu.js",
  "./files-failures.js",
  "./lock-design.js",
  "./lock.js",
  "./lock-idle.js",
  "./mycelium.js",
  "./scene.js",
  "./trails.js",
]

const failed = []
for (const suite of suites) {
  try {
    require(suite)
  } catch (error) {
    failed.push(suite)
    const head = String(error && error.stack || error).split("\n").slice(0, 6).join("\n")
    console.error(`FAIL ${suite}\n${head}\n`)
  }
}
if (failed.length) {
  console.error(`${failed.length} of ${suites.length} suites failed: ${failed.map(s => s.slice(2)).join(", ")}`)
  process.exit(1)
}
console.log(`all ${suites.length} suites passed`)
