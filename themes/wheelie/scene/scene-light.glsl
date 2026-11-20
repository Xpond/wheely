vec3 rgbToHsl(vec3 c) {
    float hi = max(c.r, max(c.g, c.b)), lo = min(c.r, min(c.g, c.b)), d = hi - lo;
    float l = (hi + lo) / 2.0;
    if (d < 0.00001) return vec3(0.0, 0.0, l);
    float h = hi == c.r ? mod((c.g - c.b) / d, 6.0) : hi == c.g ? (c.b - c.r) / d + 2.0 : (c.r - c.g) / d + 4.0;
    return vec3(h / 6.0, d / (1.0 - abs(2.0 * l - 1.0)), l);
}

vec3 hslToRgb(vec3 hsl) {
    vec3 k = mod(vec3(0.0, 8.0, 4.0) + hsl.x * 12.0, 12.0);
    return hsl.z - hsl.y * min(hsl.z, 1.0 - hsl.z) * clamp(min(k - 3.0, 9.0 - k), -1.0, 1.0);
}

// Daylight sand, for a premultiplied colour at uv in scene coordinates: the tan dunes and dust and the
// grey ground turn the theme's peach, or the storm pale cream. Saturated paint, whites, and dark rubber
// keep their colour.
vec4 daylightSand(vec4 premultiplied, vec2 uv, bool storm) {
    vec3 color = premultiplied.rgb / max(premultiplied.a, 0.0001);
    vec3 hsl = rgbToHsl(color);
    float hue = hsl.x * 360.0;
    float tan = smoothstep(0.0, 12.0, hue) * (1.0 - smoothstep(48.0, 62.0, hue))
                * smoothstep(0.10, 0.18, hsl.y) * (1.0 - smoothstep(0.50, 0.65, hsl.y));
    float ground = smoothstep(0.64, 0.68, uv.y) * (1.0 - smoothstep(0.20, 0.30, hsl.y))
                   * (1.0 - smoothstep(0.75, 0.85, hsl.z));
    float lit = pow(hsl.z, 0.55);
    vec3 sand = storm ? hslToRgb(vec3(36.0 / 360.0, max(0.85 * hsl.y, 0.22), lit))
                      : hslToRgb(vec3(22.0 / 360.0, 0.35, lit));
    float amount = max(tan, ground) * smoothstep(0.12, 0.25, hsl.z);
    return vec4(mix(color, sand, amount) * premultiplied.a, premultiplied.a);
}

// The scene's grade, for a premultiplied colour at uv in scene coordinates; light 1 grades the daylight variant.
vec4 sceneLight(vec4 premultiplied, vec2 uv, float light) {
    vec3 color = premultiplied.rgb / max(premultiplied.a, 0.0001);
    float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
    // Retain the blue sky while warming sunlit sand, paint, cloth, and metal.
    float sky = (1.0 - smoothstep(0.55, 0.70, uv.y))
                * smoothstep(0.015, 0.12, color.b - color.r);
    float ground = smoothstep(0.67, 0.82, uv.y);
    float warm = smoothstep(0.25, 0.85, luma) * (1.0 - 0.8 * sky) * (1.0 - 0.85 * ground)
                 * (1.0 - 0.75 * smoothstep(0.82, 1.0, luma));
    float cool = 1.0 - smoothstep(0.12, 0.55, luma) + 0.35 * ground * (1.0 - light); // Daylight sand is warm.
    color *= vec3(1.0) + warm * vec3(0.13, -0.015, -0.10) + cool * vec3(-0.06, -0.015, 0.04);
    color = (color - 0.5) * 1.08 + 0.5;
    color *= 1.0 - 0.07 * smoothstep(0.68, 0.90, uv.y);
    vec2 sun = (uv - vec2(0.04, 0.34)) / vec2(0.56, 0.43);
    float glow = exp(-2.4 * dot(sun, sun));
    color += (1.0 - color) * vec3(1.0, 0.52, 0.20) * 0.18 * glow;
    // Roll off bright clouds without clipping their warm hue or losing detail.
    float peak = max(color.r, max(color.g, color.b));
    if (peak > 0.9) color *= (0.9 + 0.1 * (1.0 - exp(-(peak - 0.9) / 0.1))) / peak;
    float edge = length((uv - vec2(0.56, 0.48)) * vec2(0.85, 1.0));
    color *= 1.0 - 0.10 * smoothstep(0.40, 0.78, edge);
    // The foreground falls into shade toward the bottom edge and its corners, in linear light.
    float depth = pow(clamp((uv.y - 0.729) / 0.271, 0.0, 1.0), 1.2);
    float side = (uv.x - 0.55) / 0.55;
    color *= pow(1.0 - depth * (0.55 + 0.2 * side * side), 1.0 / 2.2);
    // A vignette deepens the bottom edge, where the bar sits.
    float low = smoothstep(0.74, 1.0, uv.y);
    color *= pow(1.0 - low * (0.75 + 0.15 * side * side), 1.0 / 2.2);
    return vec4(clamp(color, 0.0, 1.0) * premultiplied.a, premultiplied.a);
}
