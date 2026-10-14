"""The production scan controller with replaceable fd commands."""
import json
import re


def fixture(wheel, block):
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
            out += "; walk: " + json.dumps(command)[:-1] + ", String(epoch)] }\n"
        return out + handlers

    return scan
