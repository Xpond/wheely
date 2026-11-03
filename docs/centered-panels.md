# Centered shell panels

Makes Omarchy's bar panels (Display, Audio, Network, Power…) open centered on
screen over a blurred desktop, instead of tucked against the bar edge beside
their widget. The wheel's **Centered panels** setting turns this off.

**Working:** centering, blur, Ctrl+Left/Right panel switching, and the
shared backdrop across handoffs. The motion is Omarchy's own since 4.5: a
centred card grows from its centre, and one switching within a bar section
morphs into the next.

## Settings

The wheel's **Centered panels** setting (type `wheely settings`) switches between centred
panels over the backdrop and Omarchy's own placement beside the bar.

Installed blur strength comes from `config/hyprland.lua` (`size 4, passes 2`);
the wheel's **Backdrop** setting turns it off at 0% ([`wheel.md`](wheel.md#settings), Settings).
Put personal overrides after the managed block in your main Hyprland config.
`passes` has the most effect; `passes 1` for a lighter frost.

## Known limits

**Latency before the first frame**, which is sluggishness rather than judder:
monitor 152ms, bluetooth 74ms, clock 44ms, network 37ms. Only `monitor` is bad
enough to notice, and it is the 4 processes `refresh()` spawns on open. Fixing it means
deferring that work until after the entry animation, in another package-owned file.

How it works, how the patches are maintained, and what was measured: [`dev/centered-panels.md`](dev/centered-panels.md).
