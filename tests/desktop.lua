local binds, layers, env, blur = {}, {}, {}, false
-- The key and blur the files under $HOME should produce, and the pause key when Wheelie is installed.
local key, blurred, pause = arg[2] or "SUPER + A", arg[3] ~= "off", arg[4]
hl = {
  dsp = { global = function(id) return { global = id } end },
  unbind = function(key) binds[key] = {} end,
  env = function(key, value) env[key] = value end,
  config = function(cfg) blur = cfg.decoration.blur.enabled end,
  layer_rule = function(rule) layers[rule.match.namespace] = rule end,
}
o = { bind = function(key, label, command, options)
  table.insert(binds[key], { command = command, release = options and options.release })
end }

dofile(arg[1])

assert(env.QSG_RENDER_LOOP == "threaded")
assert(env.QT_FFMPEG_DECODING_HW_DEVICE_TYPES == ",")
assert(#binds[key] == 1 and binds[key][1].command.global == "xpo.wheel:toggle",
  "wheel shortcut must deliver press/release directly without a subprocess")
assert(key == "SUPER + A" or binds["SUPER + A"] == nil, "SUPER + A was taken as well as " .. key)
assert(#binds["SUPER + W"] == 1 and binds["SUPER + W"][1].command == "omarchy-wheel-close")
-- Wheelie's pause key toggles its scene unless the wheel holds it; without Wheelie, CTRL + SPACE stays free.
if pause and pause ~= key then
  assert(#binds[pause] == 1 and binds[pause][1].command:find('/wheelie/wheelie" toggle', 1, true),
    "the pause key does not toggle Wheelie")
end
assert(pause == "CTRL + SPACE" or binds["CTRL + SPACE"] == nil, "CTRL + SPACE was taken as well as " .. tostring(pause))
assert(layers["omarchy-panel-scrim"].blur == blurred and blur == blurred, "the blur does not follow the file")
assert(layers["^(omarchy-wheel|omarchy-files)$"].no_anim)
assert(layers["^(omarchy-wheel|omarchy-files)$"].blur == false)
