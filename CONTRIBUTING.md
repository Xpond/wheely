# Contributing

wheely patches Omarchy's packaged shell, so most of it can only be exercised on an
Omarchy desktop. What the checks cover, what they need and how to run them is in
[`tests/README.md`](tests/README.md); `./tests/all.sh` is what a release runs.

- The user docs are `docs/*.md`; maintenance notes, measurements and the traps that cost a
  debugging round live in `docs/dev/`.
- `patches/orig/` holds the stock Omarchy shell files a patch was made against, and
  `patches/shell/` the patched ones. Keep a patch to its feature: every unrelated line makes
  the next Omarchy release harder to rebase onto.
- Shaders are committed both as GLSL and as `.qsb`; rebuild with `scripts/build-shaders.sh`
  after editing one.
- Images are AI-generated and shipped at 4K, JPEG quality 90 for photos; keep new ones in
  the same range so the repository stays small to clone.

Bugs: open an [issue](https://github.com/Xpond/wheely/issues) with what you did, what
happened, your GPU and the output of `omarchy-version` and
`quickshell log -p "$OMARCHY_PATH/shell" -t 50`.
