local binds, layers, env, blur = {}, {}, {}, false
-- The key and blur the files under $HOME should produce.
local key, blurred = arg[2] or "SUPER + A", arg[3] ~= "off"
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
assert(#binds[key] == 1 and binds[key][1].command.global == "xpo.wheel:toggle",
  "wheel shortcut must deliver press/release directly without a subprocess")
assert(key == "SUPER + A" or binds["SUPER + A"] == nil, "SUPER + A was taken as well as " .. key)
assert(#binds["SUPER + W"] == 1 and binds["SUPER + W"][1].command == "omarchy-wheel-close")
assert(layers["omarchy-panel-scrim"].blur == blurred and blur == blurred, "the blur does not follow the file")
assert(layers["^(omarchy-wheel|omarchy-files)$"].no_anim)
assert(layers["^(omarchy-wheel|omarchy-files)$"].blur == false)
