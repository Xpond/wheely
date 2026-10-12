#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 resolution;
    // Seconds of water motion, wrapped hourly.
    float time;
    float muted;
};
layout(binding = 2) uniform sampler2D surgeData;
layout(binding = 1) uniform sampler2D bubbles;

// Screen heights from centre: surge origin and permanent waterline.
const float origin = -0.6;
const float shallows = -0.32;
// Slow the backwash relative to the run-up.
const float drain = 0.6;

float hash(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash(vec2 p) { vec3 q = fract(p.xyx * 0.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y) * q.z); }

float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x), mix(hash(i + vec2(0, 1)), hash(i + vec2(1, 1)), f.x), f.y);
}
// The noise and its slope, repeating every 64 units.
vec3 sloped(vec2 p) {
    vec2 i = floor(p), f = fract(p), s = f * f * (3.0 - 2.0 * f), ds = 6.0 * f * (1.0 - f);
    float a = hash(mod(i, 64.0)), b = hash(mod(i + vec2(1, 0), 64.0));
    float c = hash(mod(i + vec2(0, 1), 64.0)), d = hash(mod(i + vec2(1, 1), 64.0));
    return vec3(a + (b - a) * s.x + (c - a) * s.y + (a - b - c + d) * s.x * s.y,
                ds * (vec2(b - a, c - a) + (a - b - c + d) * s.yx));
}
float fbm(vec2 p) { return (0.5 * noise(p) + 0.25 * noise(p * 2.03 + 1.7) + 0.125 * noise(p * 4.01 + 3.1) + 0.0625 * noise(p * 7.97 + 5.3)) / 0.9375; }

// Invert the surge's time warp, which slows the backwash.
float when(float p) { return (1.0 + drain - sqrt((1.0 + drain) * (1.0 + drain) - 4.0 * drain * p)) / (2.0 * drain); }

// Foam coverage and thickness at p (screen heights), curling with age.
vec2 foamAt(vec2 p, float density, float age) {
    if (density < 0.001) return vec2(0.0);
    density = min(density, 0.82);
    vec2 q = p * vec2(13.0, 24.0);
    vec2 bend = q * 0.4 + vec2(0.07, -0.05) * age;
    q += 1.5 * vec2(0.65 * noise(bend) + 0.35 * noise(bend * 2.1 + 3.0), 0.65 * noise(bend + 5.2) + 0.35 * noise(bend * 2.1 + 8.1));
    float n = 0.5 + 2.2 * (fbm(q) - 0.5) + 0.03 * (noise(p * 120.0) - 0.5);
    float lace = 1.0 - abs(2.0 * n - 1.0), edge = 1.0 - density;
    vec3 pore = texture(bubbles, p * vec2(6.0, 9.0)).rgb;
    float froth = smoothstep(0.16, 0.52, pore.r + 0.16 * density);
    float openings = smoothstep(0.18, 0.48, texture(bubbles, q * 0.09).r + 0.32 * density);
    float coverage = smoothstep(edge - 0.04, edge + 0.04, lace) * smoothstep(0.001, 0.06, density);
    float lighting = 0.88 + 0.08 * froth + 0.04 * dot(pore.gb * 2.0 - 1.0, vec2(-0.5, -0.85));
    float opacity = coverage * (0.2 + 0.8 * openings) * (0.75 + 0.25 * froth)
                  * (0.35 + 0.65 * smoothstep(0.1, 0.6, density)) * (0.5 + 0.5 * smoothstep(edge, edge + 0.18, lace));
    return vec2(opacity, opacity * lighting);
}

// hour is the hour fraction; whole 64-unit shifts keep the caustic wrap continuous.
float caustic(vec2 p, float hour) {
    mat2 turn = mat2(0.8, 0.6, -0.6, 0.8);
    float a = 0.65 * sloped(turn * p + vec2(64.0 * 15.0 * hour, 0.0)).x
            + 0.35 * sloped(turn * turn * p * 2.1 + vec2(0.0, 64.0 * 25.0 * hour) + 9.0).x;
    float b = 0.65 * sloped(p * 1.3 + vec2(0.0, 64.0 * 20.0 * hour) + 17.0).x
            + 0.35 * sloped(turn * p * 2.7 - vec2(64.0 * 30.0 * hour, 0.0) + 29.0).x;
    return pow(1.0 - abs(2.0 * a - 1.0), 16.0) + pow(1.0 - abs(2.0 * b - 1.0), 16.0);
}

// Dry sand has ripples and grain; wet sand is darker and smoother.
vec3 sandAt(vec2 p, float wet) {
    float grain = 0.6 * noise(p * 900.0) + 0.4 * noise(p * 1800.0 + 7.0), speck = hash(floor(p * 650.0));
    vec3 colour = mix(vec3(0.98, 0.96, 0.90), vec3(0.82, 0.87, 0.81), wet)
                * mix(vec3(1.0), vec3(1.01, 0.99, 0.97), noise(p * 3.0 + 9.0))
                * (0.97 + 0.04 * grain) * (0.98 + 0.02 * noise(p * 5.0) + 0.015 * noise(p * 11.0 + 3.0));
    colour *= 1.0 - 0.12 * step(0.994, speck);
    colour += 0.08 * step(0.997, hash(floor(p * 650.0) + 0.5)) * (1.0 - wet);
    vec2 across = normalize(vec2(0.35, 1.0));
    float phase = dot(p, across) * 190.0 + 6.0 * noise(p * vec2(1.5, 3.0));
    vec3 bump = sloped(p * 110.0 + 5.0);
    vec2 slope = (1.0 - wet) * (0.00025 * 190.0 * cos(phase) * across * smoothstep(0.35, 0.75, noise(p * 2.5 + 3.0))
                              + 0.0003 * 110.0 * bump.yz);
    return colour * (1.0 - 0.9 * dot(slope, normalize(vec2(-0.5, -0.85))));
}

void main() {
    // Fixed aerial camera: horizontal surf with a gently uneven shoreline.
    vec2 screen = (qt_TexCoord0 - 0.5) * resolution / resolution.y;
    vec2 g = screen;
    float px = 1.0 / resolution.y;
    float u = g.x, v = g.y + 0.018 * sin(g.x * 2.5) + 0.008 * sin(g.x * 5.0);

    float offshore = shallows - v, depth = 1.2 * (offshore + sqrt(offshore * offshore + 0.002));
    depth += 0.65 * smoothstep(0.15, -0.45, v); // Rich turquoise without stacked wave slabs.
    float wet = max(smoothstep(shallows + 0.25, shallows, v), 0.4), gloss = 0.0, shade = 0.0;
    vec2 foam = vec2(0.0);
    float surfTime = 148.0 + 0.65 * sin(6.2831853 * mod(time - 148.0, 6.0) / 6.0);
    float peak = when(0.5);
    // Water textures stay continuous underneath overlapping surges.
    vec2 flow = vec2(u, v);
    // Small overlapping washes move the contact edge along the sand independently.
    float washPhase = 6.2831853 * mod(time - 148.0, 3.0) / 3.0;
    v -= smoothstep(-0.12, 0.04, v) * (0.012 * sin(u * 16.0 + washPhase)
                                   + 0.006 * sin(u * 29.0 - 2.0 * washPhase));
    float covered = 0.0;
    // The tide holds near 148s: the next surge never starts and older ones have dried.
    for (int i = 0; i < 3; ++i) {
        float k = 24.0 - float(i);
        vec4 data = texture(surgeData, vec2(qt_TexCoord0.x, (float(i) + 0.5) / 4.0));
        float start = data.x;
        float span = 12.5 + 3.0 * hash(k + 0.6), since = surfTime - start;
        if (since < 0.0) continue;
        float r = data.y, s = since / span;
        float p = s * (1.0 + drain * (1.0 - s)), run = 4.0 * p * (1.0 - p) * r;
        // Ignore surges beyond their frayed reach.
        if (s < 1.0 && origin + run - v > -0.017) {
            float fray = (0.012 * (noise(vec2(u * 6.0, since * 0.7) + k) - 0.5)
                        + 0.005 * (noise(vec2(u * 18.0, since * 1.5) + k) - 0.5)) * (1.0 - smoothstep(0.35, 0.6, s));
            float d = origin + run + fray - v;
            // Draining back, the thinning film tears into patches behind its edge.
            float film = d - smoothstep(peak, 0.75, s) * 0.035 * noise(vec2(u, v) * vec2(25.0, 45.0) + 3.0 * k);
            // Foaming bore thins to an edge rope before draining.
            float rope = 0.008 * (0.8 + 0.5 * data.z) * (1.0 + 2.0 * (1.0 - smoothstep(0.0, 0.3, s)));
            float arrival = smoothstep(0.0, 0.06, s);
            float fading = arrival * (1.0 - smoothstep(0.3, 0.5, s));
            if (film > -0.004) {
                // The waterline is soft; bubbles make only the foam along it lumpy.
                wet = max(wet, smoothstep(-0.004, 0.002, film));
                // A thin wash over the sand; never stack tinted slabs over the sea.
                depth = max(depth, 0.055 * smoothstep(0.0, 0.10, film) * arrival * (1.0 - smoothstep(0.65, 1.0, s)));
                float lumpy = d + 0.003 * (data.w - 0.5);
                if (covered < 0.999 && lumpy > -0.004) {
                    // Carry foam with the front; its wake stretches and thins.
                    float cover = (1.0 - covered) * smoothstep(-0.004, 0.006, min(lumpy, film)) * arrival;
                    vec2 waveFlow = vec2(u, v - run * (0.5 + 0.5 * exp(-d / 1.5))) + 3.1 * k;
                    // Bore has ragged foam; the thinning edge rope closes up.
                    float churned = 0.78 + 0.30 * noise(waveFlow * vec2(24.0, 38.0));
                    float dense = max(churned * exp(-pow(lumpy / rope, 2.0)) * fading,
                                      0.4 * smoothstep(0.3, 0.7, noise(waveFlow * vec2(3.0, 5.0))) * (1.0 - 0.6 * s) * smoothstep(0.0, 0.03, d));
                    foam += foamAt(waveFlow, dense, since) * cover;
                    covered += cover;
                }
            }
            // The foam's shadow falls a little up the beach, on the sand ahead and the bottom below.
            float under = d + 0.008;
            if (under > 0.0)
                shade = max(shade, smoothstep(0.0, 0.01, under) * min(1.0, 1.4 * exp(-pow(under / rope, 2.0)) * fading));
        }
        // Bubbles stranded where it stopped, popping as it drains.
        float top = origin + r - v;
        if (s > peak && top > -0.005 && top < 0.02)
            foam = max(foam, foamAt(vec2(u, top) + 5.7 * k, 0.8 * smoothstep(peak, peak + 0.04, s) * exp(-pow((top - 0.003) / 0.0025, 2.0) - (s - peak) * span / 2.5), since));
        // Dry within 16s so a discarded surge no longer affects wetness.
        float q = (v - origin) / r;
        if (q < 1.0) {
            float down = when((1.0 + sqrt(1.0 - max(q, 0.0))) / 2.0);
            if (s > down) {
                float dried = (s - down) * span, edge = smoothstep(1.0, 0.98, q);
                wet = max(wet, edge * pow(max(1.0 - dried / 16.0, 0.0), 2.0));
                gloss = max(gloss, edge * smoothstep(0.0, 0.4, dried) * exp(-dried / 2.0));
            }
        }
    }

    // Three ripple trains; whole 64-unit shifts keep the hourly wrap continuous.
    float water = smoothstep(0.005, 0.03, depth), light = 0.0;
    vec2 slope = vec2(0.0);
    if (water > 0.0) {
        for (int o = 0; o < 3; ++o) {
            float turn = 0.6 + 1.9 * float(o), size = 30.0 * pow(1.9, float(o));
            mat2 spin = mat2(cos(turn), sin(turn), -sin(turn), cos(turn));
            vec3 h = sloped(spin * flow * size + vec2(0.0, 64.0 * (20.0 + 12.0 * float(o)) * time / 3600.0));
            slope += (h.yz * spin) * size / pow(2.0, float(o));
        }
        slope *= 0.0025 * water;
        light = caustic(flow * 20.0, time / 3600.0) * water * exp(-1.5 * depth) * (1.0 - foam.x);
    }
    vec3 bottom = sandAt(g - slope * min(depth, 0.6) * 0.03, wet) * (1.0 - 0.10 * shade) * (1.0 + 0.12 * light);
    // Cached positions and strength of the two old tide marks.
    vec4 grit = texture(surgeData, vec2(qt_TexCoord0.x, 0.875));
    bottom *= 1.0 - 0.035 * exp(-pow((grit.x - g.y) / (1.8 * px), 2.0)) * grit.y;
    bottom *= 1.0 - 0.035 * exp(-pow((grit.z - g.y) / (1.8 * px), 2.0)) * grit.w;
    // Seen through the water: reds go first, then the shallows turn green and turquoise.
    vec3 transmission = exp(-depth * vec3(1.30, 0.44, 0.34));
    vec3 colour = bottom * transmission + vec3(0.08, 0.47, 0.51) * (1.0 - transmission);
    // Sun is up the beach.
    vec3 n = normalize(vec3(-slope, 1.0));
    colour += water * vec3(0.75, 0.87, 1.0) * (0.04 + 0.3 * max(-n.y, 0.0));
    colour += water * (1.0 - foam.x) * 0.18 * pow(max(dot(n, normalize(vec3(0.0, -0.15, 1.0))), 0.0), 900.0);
    // Wet sand shines with the sky, freshly bared sand most, in patches as the film drains.
    colour += (1.0 - water) * (0.05 * wet + 0.08 * gloss * (0.5 + 0.5 * noise(g * 30.0))) * vec3(0.8, 0.9, 1.0);
    vec3 foamColour = vec3(0.97, 0.98, 1.0);
    if (muted > 0.5) {
        // Charcoal water and warm grey shore; thin washes retain the shore's pale colour.
        float tone = dot(clamp(colour, 0.0, 1.0), vec3(0.2126, 0.7152, 0.0722));
        colour = tone * mix(vec3(0.86, 0.85, 0.82), vec3(0.45), smoothstep(0.02, 0.16, depth));
        foamColour = mix(vec3(0.99, 0.98, 0.95), vec3(0.98), water);
    }
    colour = colour * (1.0 - foam.x) + foamColour * foam.y;
    fragColor = vec4(clamp(colour, 0.0, 1.0), 1.0) * qt_Opacity;
}
