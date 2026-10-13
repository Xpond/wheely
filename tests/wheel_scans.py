"""Scan cancellation, epochs and incremental joins in the wheel."""
import json
import re


def check(wheel, run, block):
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
  property string query: "/missing"
  readonly property string term: MenuIndex.termOf(root.query)
  property var files: null
  property var folders: """ + folders + """
  property real daylight: 0
  property string editing: ""
  function paths() { return root.files ? JSON.stringify(root.files.paths) : "null" }
""" + re.search(r"  readonly property string emptyText:.*?(?=\n\n)", wheel, re.S).group() + "\n"
        out += block(wheel, r"  component FileScan: Process \{") + "\n"
        for name, wait in [("home", seconds), ("folder", folder_seconds)]:
            command = ["sh", "-c", "sleep " + wait + '; printf "/epoch-%s/' + name + '\\n" "$1"', "scan"]
            out += "  FileScan { id: " + name + "Scan; command: " + json.dumps(command)[:-1] + ", String(epoch)] }\n"
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
    if (root.files !== null || homeScan.running) { console.error("FAIL retained scan"); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
''')

    # Complete lines appear while fd still runs; an unfinished line waits for its newline.
    run("scan-streaming", scan("5") + r'''
  Component.onCompleted: {
    homeScan.command = ["sh", "-c", "printf '/first path\\n/part'; sleep .3; printf 'ial\\n'; sleep .3"]
    root.mode = "file"
  }
  Timer { interval: 150; running: true; onTriggered: {
    if (root.paths() !== '["/first path"]' || !homeScan.running) {
      console.error("FAIL did not stream complete lines", root.paths()); Qt.exit(1)
    }
  } }
  Timer { interval: 450; running: true; onTriggered: {
    if (root.paths() !== '["/first path","/partial"]' || !homeScan.running) {
      console.error("FAIL lost partial line", root.paths()); Qt.exit(1)
    }
    root.opened = false
  } }
  Timer { interval: 700; running: true; onTriggered: {
    if (root.files !== null) { console.error("FAIL stale batch after close"); Qt.exit(1) }
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

    # The skip list's suggestions are home's scanned folders, so showing it scans home as `/` does,
    # and leaves the added folders unscanned.
    run("scan-skip-list", scan("0.05", "0.05", '["/x"]') + """
  Component.onCompleted: root.listing = "skipped"
  Timer { interval: 400; running: true; onTriggered: {
    if (root.paths() !== '["/epoch-0/home"]') { console.error("FAIL the skip list scanned", root.paths()); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")

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
    if (root.paths() !== '["/epoch-0/home","/epoch-0/folder"]') { console.error("FAIL late", root.paths()); Qt.exit(1) }
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
    if (root.paths() !== '["/epoch-1/home","/epoch-1/folder"]') { console.error("FAIL rescanned", root.paths()); Qt.exit(1) }
    else { console.log("PASS"); Qt.quit() }
  } }
""")
