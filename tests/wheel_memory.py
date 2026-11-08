"""Deferred collection after a file search, using the production close handlers."""


def check(scan, run):
    # Count the native collection call without changing the timer's production guards.
    observed = scan("5").replace("gc()", "{ root.collections++; gc() }") + "\n  property int collections: 0\n"
    run("scan-collect-after-close", observed + """
  Component.onCompleted: {
    root.opened = false
    if (scanCleanup.running) { console.error("FAIL collected without a search"); Qt.exit(1); return }
    root.opened = true; root.mode = "file"
  }
  Timer { interval: 30; running: true; onTriggered: {
    root.opened = false
    if (root.collections || !scanCleanup.running || root.fileWorker) {
      console.error("FAIL cleanup was not deferred past unload"); Qt.exit(1)
    }
  } }
  Timer { interval: 500; running: true; onTriggered: {
    if (root.collections !== 1) { console.error("FAIL collections", root.collections); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")
    for visible in ("opened", "windowed"):
        run("scan-collect-cancel-" + visible, observed + """
  Component.onCompleted: root.mode = "file"
  Timer { interval: 30; running: true; onTriggered: root.opened = false }
  Timer { interval: 80; running: true; onTriggered: root.""" + visible + """ = true }
  Timer { interval: 500; running: true; onTriggered: {
    if (root.collections) { console.error("FAIL collected while visible"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")

    run("scan-collect-pinned-close", observed + """
  Component.onCompleted: { root.windowed = true; root.mode = "file" }
  Timer { interval: 30; running: true; onTriggered: root.opened = false }
  Timer { interval: 350; running: true; onTriggered: {
    if (!root.fileWorker || root.collections || scanCleanup.running) {
      console.error("FAIL pinned search collected"); Qt.exit(1); return
    }
    root.windowed = false; root.dropScan()
  } }
  Timer { interval: 700; running: true; onTriggered: {
    if (root.fileWorker || root.collections !== 1) { console.error("FAIL pinned close", root.collections); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")
