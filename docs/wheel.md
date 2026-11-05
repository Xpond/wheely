# The wheel

A radial launcher for Omarchy. Tap `SUPER+A` (or your own key, see Settings): your
bar's panels sit on a ring, and typing turns the centre into one search for anything.

Every key is in the manual: type `help` in the wheel, or see
[`manual.md`](../plugins/xpo.wheel/manual.md).

## The ring

`↑` `↓` jump to the slice at that compass point, `←` `→` and `Tab` step around, and
`Enter` opens it. With the mouse, flick or click toward a slice, or scroll to step.
`Backspace` goes back, including from a panel the wheel opened. `Esc` clears, goes back,
then closes. `SUPER+W` closes the wheel and whatever it opened. Hold an arrow key for a
few seconds for a surprise.

## Search

Start typing to search the Omarchy menu, apps, open windows, keybindings, themes,
fonts, settings and the manual. Rows you pick often rise to the top.

| type | finds |
|---|---|
| anything | everything above |
| `workspace` | every open window; `workspace 2` the ones on 2 |
| `/` | files and folders under home and any folders you add |
| `=` | a calculation; `Enter` copies the answer |
| `help` | the manual; `Enter` shows it on one screen |
| `wheely settings` | the wheel's settings |

On a file, `Enter` opens it in [Files](files.md), `Ctrl+Y` copies its path and
`Ctrl+Enter` opens a terminal in its folder.

## Pinning

`Ctrl+T` turns the search into a normal window that stays open beside your others:
each pick runs and the search is ready for the next. `Ctrl+T` again brings it back to
the wheel.

## Settings

Type `wheely settings`; `Enter` changes one without closing the wheel.

| setting | what it does |
|---|---|
| Wheely shortcut | the key that opens the wheel; must include SUPER |
| Wallpaper pause | the key that pauses Wheelie's or Tidal's animation |
| Wheely ring | edit which slices the ring shows (below) |
| Backdrop | how much the backdrop blurs and dims the desktop |
| Centered panels | bar panels centered over the backdrop, or beside their widget |
| Searched folders | more folders for `/` to search |
| Skipped folders | folders `/` never searches |
| Wheely history | your past picks |
| Forget picks | reset what the wheel has learned you use |

## Your own ring

By default the ring shows your bar's panels and follows the bar. To choose it yourself,
open **Wheely ring**: type to find anything and `Enter` adds it, `Del` removes the
selected slice, `Shift+←` `Shift+→` move it, and `Ctrl+R` twice resets to the bar.
Changes save as you make them.

## Known limits

- The pinned search has no ring, so submenus, the ring editor and recording a shortcut
  work from the wheel only. Its results do not scroll with the mouse wheel.
- A window is found by its title or app id, not by what runs inside it: search `kitty`
  to list every kitty window.

How it is built: [`dev/wheel.md`](dev/wheel.md).
