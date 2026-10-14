"""Scan cancellation, epochs and incremental joins in the wheel."""
import json
import re


def check(wheel, run_case, block):
    def run(name, body):
        # Quickshell emits this even for an isolated WorkerScript that only echoes its input.
        return run_case(name, body, expected=(re.escape("QObject::connect(QJSEngine, QtObject): invalid nullptr parameter"),))

    # A wheel's scan state around the real walks, with `fd` swapped for scans that say which
    # epoch asked for them. Everything else -- the epoch, the guards, the join -- is production code.
    handlers = wheel[wheel.index("  property int scanEpoch:"):wheel.index(
        "  // Omarchy's menu re-checks its rows on every open")]

    def scan(seconds, folder_seconds="0.05", folders="[]"):
        out = """
  property bool opened: true
  property bool windowed: false
  property string mode: ""
  property string listing: ""
  property string query: "//"
  property string home: "/home"
  property var uses: ({})
  readonly property string term: MenuIndex.termOf(root.query)
  property bool filesReady: false
  property var folders: """ + folders + """
  property real daylight: 0
  property string editing: ""
  function paths() { return root.filesReady ? JSON.stringify(root.fileResults.map(e => e.path).sort()) : "null" }
""" + re.search(r"  readonly property string emptyText:.*?(?=\n\n)", wheel, re.S).group() + "\n"
        out += wheel[wheel.index("  property var fileResults:"):wheel.index("  component FileScan:")]
        out += block(wheel, r"  component FileScan: Process \{") + "\n"
        for name, wait in [("home", seconds), ("folder", folder_seconds)]:
            command = ["sh", "-c", "sleep " + wait + '; printf "/epoch-%s/' + name + '\\n" "$1"', "scan"]
            out += "  FileScan { id: " + name + "Scan; source: " + json.dumps("home" if name == "home" else "folders")
            out += "; command: " + json.dumps(command)[:-1] + ", String(epoch)] }\n"
        return out + handlers

    run("scan-close-reopen", scan("0.15") + """
  Component.onCompleted: root.mode = "file"
  Timer { interval: 30; running: true; onTriggered: {
    root.opened = false; root.opened = true; root.scanFiles()
  } }
  Timer { interval: 600; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-1/home"]') { console.error("FAIL stale scan", root.paths()); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")
    run("scan-close", scan("5") + r'''
  Component.onCompleted: {
    homeScan.command = ["sh", "-c", "printf '/pending\\n'; sleep 5"]
    root.mode = "file"
  }
  Timer { interval: 30; running: true; onTriggered: root.opened = false }
  Timer { interval: 500; running: true; onTriggered: {
    if (root.filesReady || homeScan.running) { console.error("FAIL retained scan"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')

    # Complete lines appear while fd runs; a split UTF-8 character waits for its whole line.
    run("scan-streaming", scan("5") + r'''
  Component.onCompleted: {
    homeScan.command = ["sh", "-c", "printf '/first path\\n/caf\\303'; sleep .3; printf '\\251\\n'; sleep .3"]
    root.mode = "file"
  }
  Timer { interval: 150; running: true; onTriggered: {
    if (root.paths() !== '["/first path"]' || !homeScan.running) {
      console.error("FAIL did not stream complete lines", root.paths()); Qt.exit(1)
    }
  } }
  Timer { interval: 450; running: true; onTriggered: {
    if (root.paths() !== '["/café","/first path"]' || !homeScan.running) {
      console.error("FAIL lost partial line", root.paths()); Qt.exit(1)
    }
    root.opened = false
  } }
  Timer { interval: 700; running: true; onTriggered: {
    if (root.filesReady) { console.error("FAIL stale batch after close"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')

    # An empty completed walk must stop saying Scanning and must not restart on every keystroke.
    run("scan-empty", scan("5") + '''
  Component.onCompleted: { homeScan.command = ["true"]; root.mode = "file" }
  Timer { interval: 200; running: true; onTriggered: {
    if (root.paths() !== '[]' || homeScan.running) { console.error("FAIL empty scan"); Qt.exit(1); return }
    root.scanFiles()
    if (homeScan.running) { console.error("FAIL restarted empty scan"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')

    # Empty output on a new scan must not reuse the collector's previous text.
    run("scan-empty-reopen", scan("0.02") + '''
  Component.onCompleted: root.mode = "file"
  Timer { interval: 150; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-0/home"]') { console.error("FAIL initial scan"); Qt.exit(1); return }
    root.opened = false; homeScan.command = ["true"]
    root.opened = true; root.scanFiles()
  } }
  Timer { interval: 350; running: true; onTriggered: {
    if (root.paths() !== '[]') { console.error("FAIL retained old output", root.paths()); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')

    # The skip list scans home alone, leaving added folders unscanned.
    run("scan-skip-list", scan("0.05", "0.05", '["/x"]') + """
  Component.onCompleted: root.listing = "skipped"
  Timer { interval: 400; running: true; onTriggered: {
    if (!root.filesReady || !homeScan.published || folderScan.published) { console.error("FAIL skip scan"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")

    # Typing while the worker ranks a batch must coalesce to the latest query.
    run("scan-latest-query", scan("5") + '''
  property bool changed: false
  onFileBusyChanged: if (root.fileBusy && !root.changed) {
    root.changed = true
    Qt.callLater(function () { root.query = "/beta"; root.query = "/gamma" })
  }
  onFileResultsChanged: {
    if (root.query === "/gamma" && root.fileResults.some(e => e.label !== "gamma")) {
      console.error("FAIL published an obsolete query"); Qt.exit(1)
    }
  }
  Component.onCompleted: {
    homeScan.command = ["python3", "-c", "print('/home/alpha' + chr(10), end=''); print(('/home/beta' + chr(10)) * 50000, end=''); print('/home/gamma')"]
    root.mode = "file"
  }
  Timer { interval: 800; running: true; onTriggered: {
    if (!root.changed || root.paths() !== '["/home/gamma"]' || root.fileBusy) {
      console.error("FAIL latest query", root.paths()); Qt.exit(1)
    } else { console.log("PASS"); Qt.quit() }
  } }
''')

    # Subfolders are listed only while a path is typed into the folders list: a model with no
    # folder lists the working directory and watches it.
    run("subfolders-on-demand", """
  property string listing: ""
  property string query: ""
""" + block(wheel, r"  readonly property var subfolderPaths:") + "\n"
        + block(wheel, r"  Loader \{\n    id: subfolders") + """
  Timer { interval: 300; running: true; onTriggered: {
    if (subfolders.item || root.subfolderPaths.length) { console.error("FAIL listed", root.subfolderPaths); Qt.exit(1) }
    root.listing = "folders"; root.query = "/us"
  } }
  Timer { interval: 900; running: true; onTriggered: {
    if (root.subfolderPaths.indexOf("/usr") < 0) { console.error("FAIL /", root.subfolderPaths); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")

    # An added folder appears without waiting for home's slower scan, then joins it when home lands.
    run("scan-folder-first", scan("0.6", "0.05", '["/x"]') + """
  Component.onCompleted: root.mode = "file"
  Timer { interval: 400; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-0/folder"]') { console.error("FAIL held folder", root.paths()); Qt.exit(1) }
    if (root.emptyText !== "Scanning\\u2026") { console.error("FAIL home still scanning"); Qt.exit(1) }
  } }
  Timer { interval: 1600; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-0/folder","/epoch-0/home"]') { console.error("FAIL late", root.paths()); Qt.exit(1) }
    else if (root.emptyText !== "No match") { console.error("FAIL completed scan"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")

    # A finished scan is the open's own: reopening scans again, and home's new paths never show
    # beside the last open's folder paths.
    run("scan-done-reopen", scan("0.05", "0.3", '["/x"]') + """
  Component.onCompleted: root.mode = "file"
  Timer { interval: 600; running: true; onTriggered: { root.opened = false; root.opened = true; root.scanFiles() } }
  Timer { interval: 800; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-1/home"]') { console.error("FAIL reopened", root.paths()); Qt.exit(1) }
    if (root.emptyText !== "Scanning\\u2026") { console.error("FAIL folder still scanning"); Qt.exit(1) }
  } }
  Timer { interval: 1400; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-1/folder","/epoch-1/home"]') { console.error("FAIL rescanned", root.paths()); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")
