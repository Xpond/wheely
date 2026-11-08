// The batched condition script: one pacman query and shared readers answer simple checks,
// and every other condition keeps the meaning Bash alone gives it.
const assert = require("node:assert/strict")
const fs = require("node:fs")
const os = require("node:os")
const path = require("node:path")
const { execFileSync } = require("node:child_process")
const { library } = require("./qml.js")
const M = library("plugins/xpo.wheel/MenuIndex.js")
const stubs = fs.mkdtempSync(path.join(os.tmpdir(), "wheel-conditions-"))
const stub = (name, body) => fs.writeFileSync(path.join(stubs, name), "#!/bin/bash\n" + body, { mode: 0o755 })
stub("pacman", 'echo "$1" >> "$STUBS/pacman.log"; installed=" kitty vim "\n'
  + '[[ $1 == -T && $PACMAN_FAILS ]] && exit 1\n'
  + 'if [[ $1 == -T ]]; then shift 2; s=0; for p; do [[ $installed == *" $p "* ]] || { echo "$p"; s=127; }; done; exit $s; fi\n'
  + '[[ $installed == *" $2 "* ]]\n')
stub("omarchy-default-browser", 'echo browser >> "$STUBS/reads.log"; echo "${TEST_BROWSER:-brave}"\n')
stub("omarchy-lock-design", '[[ $1 == current ]] && echo meadow\n')
stub("omarchy-bar", 'echo "bar $*" >> "$STUBS/reads.log"; [[ $* == position ]] && echo top\n'
  + '[[ $* == "get omarchy.clock verticalFormat" ]] && printf "dd\\nMMM\\n\'W\'ww\\n\'\'yy\\n"; true\n')
stub("omarchy-hw-x86", 'echo x86 >> "$STUBS/reads.log"; exit 1\n')
stub("probe-reader", 'echo probe >> "$STUBS/reads.log"; echo value\n')
// What a script printed, and which pacman queries and readers it ran.
function bash(script, fails = "") {
  for (const log of ["pacman.log", "reads.log"]) fs.writeFileSync(path.join(stubs, log), "")
  const stdout = execFileSync("bash", ["-c", script], { encoding: "utf8",
    env: { ...process.env, PATH: stubs + ":" + process.env.PATH, STUBS: stubs, PACMAN_FAILS: fails } })
  const log = name => fs.readFileSync(path.join(stubs, name), "utf8")
  return { stdout, pacman: log("pacman.log"), reads: log("reads.log") }
}
try {
  const checks = M.merge({
    kitty: { label: "Kitty", action: "k", when: "omarchy-pkg-present kitty" },
    steam: { label: "Steam", action: "s", when: "! omarchy-pkg-present steam" },
    both: { label: "Both", action: "b", when: "omarchy-pkg-missing kitty vim" },
    brave: { label: "Brave", action: "b", checked: "[[ \"$(omarchy-default-browser)\" == brave ]]" },
    zen: { label: "Zen", action: "z", checked: "[[ $(omarchy-default-browser) == zen ]]" },
    quoted: { label: "Quoted", action: "q", when: "[[ \"$(echo ')')\" == ')' ]]" },
    // A reader is asked in subshells and compound checks, and answers once; a setter is no read.
    barTop: { label: "Top", action: "t", checked: "[[ $(omarchy-bar position) != left && $(omarchy-bar position) != right ]]" },
    barLeft: { label: "Left", action: "l", checked: "[[ \"$(omarchy-bar position)\" == left ]]" },
    clock: { checked: "[[ $(omarchy-bar get omarchy.clock verticalFormat) == $'dd\\nMMM\\n\\'W\\'ww\\n\\'\\'yy' ]]" },
    clockOther: { checked: "[[ $(omarchy-bar get omarchy.clock verticalFormat) == $'HH\\nmm' ]]" },
    barStillTop: { checked: "[[ $(omarchy-bar position) == $'top' ]]" },
    barSet: { label: "Set", action: "s", when: "omarchy-bar position top" },
    x86: { label: "X86", action: "x", when: "omarchy-hw-x86" },
    notX86: { label: "Not x86", action: "n", when: "! omarchy-hw-x86" }
  }, M.lockItems(["rally", "meadow"]))
  // A failed query asks pacman per name, as omarchy-pkg-present does.
  for (const fails of ["", "1"]) {
    const run = bash(M.conditionScript(checks), fails)
    assert.deepEqual(run.stdout.trim().split("\n").sort(), ["barSet:w", "barStillTop:c", "barTop:c", "brave:c", "clock:c", "kitty:w", "notX86:w", "quoted:w", "steam:w", "style.lockscreen.1:c"])
    assert.equal(run.pacman, fails ? "-T\n-Q\n-Q\n-Q\n-Q\n" : "-T\n")
    assert.deepEqual(run.reads.trim().split("\n").sort(), ["bar get omarchy.clock verticalFormat", "bar position", "bar position top", "browser", "x86"],
      "a shared reader ran twice, or a setter was answered from a read")
  }
  const custom = {
    assignment: "probe=$(command -v wheel-test-no-such-command)",
    shortCircuit: "false && [[ $(probe-reader) == value ]]",
    guardedKnownReader: "false && [[ $(omarchy-default-browser) == brave ]]",
    literal: "[[ '$(probe-reader)' == '$'\"(probe-reader)\" ]]",
    localEnvironment: "export TEST_BROWSER=firefox; [[ $(omarchy-default-browser) == firefox ]]",
    nested: '[[ "$(printf x$(probe-reader))" == xvalue ]]',
    ordinary: "[[ $(probe-reader) == value ]]",
    quotedArgument: "[[ $(printf '%s' value) == value ]]",
    ansiLiteral: "[[ $(omarchy-default-browser) != $'$(probe-reader)' ]]"
  }
  for (const [name, expr] of Object.entries(custom)) {
    for (const [field, tag] of [["when", "w"], ["checked", "c"]]) {
      const batch = bash(M.conditionScript({ test: { [field]: expr } }))
      const alone = bash(`if { ${expr}; } >/dev/null 2>&1; then echo test:${tag}; fi`)
      assert.deepEqual([batch.stdout, batch.reads], [alone.stdout, alone.reads],
        `${name} (${field}) changed its result or executed an extra command`)
    }
  }
  // Sharing must not shadow executable lookup or outlive a custom check's environment changes.
  M.CONDITION_READERS.push("wheel-test-absent-reader")
  const sequences = [
    ["command -v wheel-test-absent-reader", '[[ $(command -v omarchy-default-browser) == "$STUBS/omarchy-default-browser" ]]'],
    ['[[ $(omarchy-default-browser) == brave ]]',
     'export TEST_BROWSER=firefox; [[ $(omarchy-default-browser) == firefox ]]',
     '[[ $(omarchy-default-browser) == firefox ]]', '[[ $(omarchy-default-browser) == firefox ]]'],
    ['[[ $(omarchy-default-browser) == brave ]]',
     '[[ $(TEST_BROWSER=firefox omarchy-default-browser) == firefox ]]',
     '[[ $(omarchy-default-browser) == brave ]]'],
    ['[[ $(omarchy-default-browser) == brave ]]',
     'omarchy-default-browser() { echo firefox; }; true',
     '[[ $(omarchy-default-browser) == firefox ]]'],
    ["[[ '$(omarchy-default-browser) == brave' == '$(omarchy-default-browser) == brave' ]]",
     "[[ $(omarchy-default-browser) == '$(omarchy-default-browser)' ]]"],
  ]
  for (const expressions of sequences) {
    const items = Object.fromEntries(expressions.map((when, i) => ["check" + i, { when }]))
    const plain = expressions.map((expr, i) => `if { ${expr}; } >/dev/null 2>&1; then echo check${i}:w; fi`).join("\n")
    assert.equal(bash(M.conditionScript(items)).stdout, bash(plain).stdout,
      "shared readers changed command lookup, environment, function lookup, or literal text")
  }
  console.log("ok: one pacman query and shared simple readers; custom conditions keep their Bash meaning")
} finally {
  fs.rmSync(stubs, { recursive: true })
}
