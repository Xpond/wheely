#!/usr/bin/env python3
"""Opt-in headless scan/typing probe; synthetic paths, not a live filesystem walk."""
import argparse
import json
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import tempfile
import time
from wheel_scan_fixture import fixture
import qslog


repo = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--counts", nargs="+", type=int, default=[83000, 497000])
parser.add_argument("--runs", type=int, default=3)
parser.add_argument("--compare", help="also measure this git revision against the same generated paths")
parser.add_argument("--batch-delay-ms", type=float, default=0, help="delay between 8 KiB producer writes; 0 uses cat")
args = parser.parse_args()


def source(name, revision):
    path = "plugins/xpo.wheel/" + name
    if revision:
        return subprocess.check_output(["git", "show", revision + ":" + path], cwd=repo, text=True)
    return (repo / path).read_text()


def block(text, pattern):
    return re.search(pattern + r".*?^  }", text, re.S | re.M).group()


def measure(base, snapshot, revision):
    wheel = source("Wheel.qml", revision)
    modern = 'source: "FileWorker.js"' in wheel
    for name in ["MenuIndex.js"] + (["FileWorker.js", "scan.py"] if modern else []):
        (base / name).write_text(source(name, revision))
    body = fixture(wheel, block)("5")
    if not modern:
        body = body.replace("; walk:", "; command:")
    walk = "walk" if modern else "command"
    command = ["cat", str(snapshot)]
    if args.batch_delay_ms:
        command = ["python3", "-c", "import sys,time; f=open(sys.argv[1],'rb'); "
                   "out=sys.stdout.buffer\nwhile chunk:=f.read(8192): "
                   "out.write(chunk); out.flush(); time.sleep(float(sys.argv[2])/1000)",
                   str(snapshot), str(args.batch_delay_ms)]
    body += '''
  property double started: 0
  property double first: 0
  property double scanned: 0
  property double heartbeat: 0
  property double scanGap: 0
  property double typingGap: 0
  property double keyAt: 0
  property var latency: []
  property int lastRequest: -1
  property bool more: false
  property int phase: 0
  property int key: 0
  property int blanks: 0
  property var queries: ["/r", "/re", "/rep", "/repo", "/report", "/image", "/notes"]
  Connections {
    target: fileWorker
    function onMessage(m) {
      if (m.reset || m.epoch !== root.scanEpoch) return
      root.more = !!m.more
      if (m.request !== root.fileRequest || m.rows === undefined) return
      if (!root.first && m.rows.length) root.first = Date.now() - root.started
      if (root.phase === 1 && root.lastRequest !== m.request) root.latency.push(Date.now() - root.keyAt)
      root.lastRequest = m.request
    }
  }
  onFileResultsChanged: if (root.phase && !root.fileResults.length) root.blanks++
  Timer { interval: 16; running: true; repeat: true; onTriggered: {
    var now = Date.now(), gap = Math.max(0, now - root.heartbeat - 16)
    if (root.heartbeat) {
      if (!root.phase) root.scanGap = Math.max(root.scanGap, gap)
      else root.typingGap = Math.max(root.typingGap, gap)
    }
    root.heartbeat = now
  } }
  Timer { interval: 5; running: true; repeat: true; onTriggered: {
    if (homeScan.running || root.fileBusy || root.more || root.fileQueue.length || root.lastRequest !== root.fileRequest) return
    if (!root.phase) {
      root.scanned = Date.now() - root.started
      root.phase = 1
      typeKey.start()
    } else if (root.key === root.queries.length && !typeKey.running) {
      console.log("MEASURE", JSON.stringify({ first_ms: root.first, scan_ms: root.scanned,
        scan_delay_ms: root.scanGap, typing_delay_ms: root.typingGap,
        last_key_ms: Date.now() - root.keyAt, replies: root.latency.length, blanks: root.blanks }))
      Qt.quit()
    }
  } }
  Timer { id: typeKey; interval: 20; repeat: true; onTriggered: {
    root.keyAt = Date.now(); root.query = root.queries[root.key++]
    if (root.key === root.queries.length) stop()
  } }
  Timer { interval: 30000; running: true; onTriggered: { console.error("FAIL timeout"); Qt.exit(1) } }
  Component.onCompleted: {
''' + f'    homeScan.{walk} = {json.dumps(command)}\n' + '''
    root.query = "/report"; root.started = Date.now(); root.mode = "file"
  }
'''
    qml = base / "probe.qml"
    qml.write_text('''import QtQuick
import QtQml.WorkerScript
import Quickshell
import Quickshell.Io
import "MenuIndex.js" as MenuIndex
Scope {
  id: root
''' + body + "\n}\n")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="generic",
               XDG_RUNTIME_DIR=str(base / "runtime"), XDG_CACHE_HOME=str(base / "cache"))
    # Sample cumulative main-thread CPU as well as heartbeat delays: small repeated stalls count.
    with (base / "log").open("w+") as log:
        child = subprocess.Popen(["quickshell", "--no-color", "-p", str(qml)], env=env, stdout=log, stderr=log)
        cpu = 0
        while child.poll() is None:
            try:
                fields = Path(f"/proc/{child.pid}/task/{child.pid}/stat").read_text().rsplit(")", 1)[1].split()
                cpu = max(cpu, int(fields[11]) + int(fields[12]))
            except FileNotFoundError:
                pass
            time.sleep(0.005)
        log.seek(0)
        text = log.read()
    assert child.returncode == 0 and "MEASURE" in text, text
    qslog.check(text, re.escape("QObject::connect(QJSEngine, QtObject): invalid nullptr parameter"))
    result = json.loads(re.search(r"MEASURE (\{.*\})", text)[1])
    result["ui_cpu_ms"] = cpu * 1000 / os.sysconf("SC_CLK_TCK")
    return result


with tempfile.TemporaryDirectory(prefix="wheel-performance-") as temporary:
    base = Path(temporary)
    for count in args.counts:
        snapshot = base / "paths.txt"
        rng = random.Random(36)
        with snapshot.open("w") as stream:
            for i in range(count):
                name = rng.choice(["report", "image", "notes", "config", "café"])
                stream.write(f"/home/bench/project-{i % 307:03}/source/{name}-{i:07}.txt\n")
        for revision in ([args.compare] if args.compare else []) + [None]:
            results = [measure(base, snapshot, revision) for _ in range(args.runs)]
            medians = {key: statistics.median(row[key] for row in results) for key in results[0]}
            print(json.dumps({"revision": revision or "working", "paths": count, "runs": args.runs,
                              "batch_delay_ms": args.batch_delay_ms,
                              "median": medians}), flush=True)
