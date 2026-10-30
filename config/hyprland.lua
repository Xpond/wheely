-- The compositor exports this before its startup callbacks launch Quickshell.
hl.env("QSG_RENDER_LOOP", "threaded")
-- Qt picks hardware decoding even for codecs the GPU lacks (AV1 on older cards) and shows black
-- without falling back, so Files' video previews decode in software. A comma means an empty device list.
hl.env("QT_FFMPEG_DECODING_HW_DEVICE_TYPES", ",")

-- The wheel's backdrop row saves "off" here at 0%, as data; anything else keeps the backdrop blurred.
local blur_file = io.open(os.getenv("HOME") .. "/.config/omarchy/wheel-blur")
local backdrop_blur = not (blur_file and blur_file:read("*l") or ""):match("^%s*off%s*$")
if blur_file then blur_file:close() end
-- Omarchy leaves Hyprland's blur off; only the backdrop turns it on, so windows stay unblurred unless the
-- user's own config blurs them.
if backdrop_blur then
  if not hl.get_config("decoration.blur.enabled") then
    hl.window_rule({ match = { class = ".*" }, no_blur = true })
  end
  hl.config({ decoration = { blur = { enabled = true, size = 4, passes = 2 } } })
end

-- Blur only the shared backdrop; blurring the overlays doubles the work. No ignore_alpha, so a light
-- dim keeps its blur.
hl.layer_rule({
  match = { namespace = "omarchy-panel-scrim" },
  blur = backdrop_blur,
  no_anim = true,
  animation = "none",
})
hl.layer_rule({
  match = { namespace = "^(omarchy-wheel|omarchy-files)$" },
  blur = false,
  no_anim = true,
  animation = "none",
})

-- The wheel's shortcut rows save their keys in ~/.config/omarchy, as data; anything unreadable keeps
-- the default.
local function saved_key(name, default)
  local file = io.open(os.getenv("HOME") .. "/.config/omarchy/" .. name)
  local saved = (file and file:read("*l") or ""):match("^%s*(.-)%s*$")
  if file then file:close() end
  if saved:match("^[%u%d_][%u%d_ +]*[%u%d_]$") and saved:find(" + ", 1, true) then return saved end
  return default
end

-- With an animated theme installed, the wallpaper pause key toggles the active theme. It is bound
-- before the wheel's keys, so they win a clash.
for _, theme in ipairs({ "wheelie", "tidal" }) do
  local controller = io.open(os.getenv("HOME") .. "/.config/omarchy/themes/" .. theme .. "/" .. theme)
  if controller then
    controller:close()
    local pause_key = saved_key("wallpaper-pause-shortcut", "CTRL + SPACE")
    hl.unbind(pause_key)
    o.bind(pause_key, "Pause/resume wallpaper", "omarchy-wallpaper-toggle")
    break
  end
end

-- The global shortcut delivers both press and release directly to the wheel.
local wheel_key = saved_key("wheel-shortcut", "SUPER + A")
hl.unbind(wheel_key)
o.bind(wheel_key, "Wheel", hl.dsp.global("xpo.wheel:toggle"))

-- SUPER+W normally closes a window; the helper retains that fallback, and so does a missing helper.
hl.unbind("SUPER + W")
o.bind("SUPER + W", "Close wheel or window",
  "command -v omarchy-wheel-close >/dev/null && exec omarchy-wheel-close; hyprctl dispatch 'hl.dsp.window.close()'")
