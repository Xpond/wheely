local binds, layers, blur, windows = {}, {}, false, {}
-- The key and blur the files under $HOME should produce, and the pause key for an animated theme.
-- A blur of "user" is the backdrop's blur under a user config that already blurs windows.
local key, blurred, pause = arg[2] or "SUPER + A", arg[3] ~= "off", arg[4]
local user_blur = arg[3] == "user"
hl = {
  dsp = { global = function(id) return { global = id } end },
  unbind = function(key) binds[key] = {} end,
  config = function(cfg) blur = cfg.decoration.blur.enabled end,
  get_config = function() return user_blur end,
  layer_rule = function(rule) layers[rule.match.namespace] = rule end,
  window_rule = function(rule) table.insert(windows, rule) end,
}
o = { bind = function(key, label, command, options)
  table.insert(binds[key], { command = command, release = options and options.release })
end }

dofile(arg[1])

assert(#binds[key] == 1 and binds[key][1].command.global == "xpo.wheel:toggle",
  "wheel shortcut must deliver press/release directly without a subprocess")
assert(key == "SUPER + A" or binds["SUPER + A"] == nil, "SUPER + A was taken as well as " .. key)
assert(#binds["SUPER + W"] == 1 and binds["SUPER + W"][1].command:find("exec omarchy-wheel-close;", 1, true))
-- The pause key toggles the active theme unless the wheel holds it; without a theme it stays free.
if pause and pause ~= key then
  assert(#binds[pause] == 1 and binds[pause][1].command == "omarchy-wallpaper-toggle",
    "the pause key does not toggle the active wallpaper")
end
assert(pause == "CTRL + SPACE" or binds["CTRL + SPACE"] == nil, "CTRL + SPACE was taken as well as " .. tostring(pause))
assert(layers["omarchy-panel-scrim"].blur == blurred and blur == blurred, "the blur does not follow the file")
-- Windows keep the blur they had: none from Omarchy, the user's own if their config sets it.
local unblurred = #windows == 1 and windows[1].match.class == ".*" and windows[1].no_blur == true
assert(unblurred == (blurred and not user_blur), "the backdrop's blur changed the windows' blur")
assert(layers["^(omarchy-wheel|omarchy-files)$"].no_anim)
assert(layers["^(omarchy-wheel|omarchy-files)$"].blur == false)
