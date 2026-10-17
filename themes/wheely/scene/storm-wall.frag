#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float approach;
    float phase;
    float sceneAspect;
    float textureAspect;
    float extent;
};
layout(binding = 1) uniform sampler2D sky;
layout(binding = 2) uniform sampler2D storm;

float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1, 0)), f.x),
               mix(hash(i + vec2(0, 1)), hash(i + vec2(1)), f.x), f.y);
}

void main() {
    vec2 uv = vec2(qt_TexCoord0.x, qt_TexCoord0.y * extent);
    // Deepen the pale upper sky behind the storm so its sunlit crest stands out.
    vec4 dusk = vec4(0.10, 0.22, 0.45, 1.0) * 0.6 * (1.0 - smoothstep(0.0, 0.8, uv.y));
    float zoom = mix(1.03, 1.15, approach);
    float height = sceneAspect / max(textureAspect, 0.01) * zoom;
    float top = 0.65 - 0.66 * height - 0.05 * approach;
    vec2 st = vec2(0.5 + (uv.x - 0.5) / zoom, (uv.y - top) / height);
    if (st.y < 0.0 || st.y > 1.0) {
        fragColor = dusk * qt_Opacity;
        return;
    }

    // Gently roll the textured billows; retain their fine dust structure.
    vec2 drift = vec2(sin(phase), cos(phase)) * 2.5;
    vec2 p = st * vec2(12.0, 6.0);
    st += vec2(0.012 * (noise(p + drift) - 0.5),
               0.018 * (noise(p + drift + vec2(5.2, 1.7)) - 0.5));
    st = clamp(st, vec2(0.0), vec2(1.0));
    vec3 plate = texture(storm, st).rgb;
    vec3 back = texture(sky, st).rgb;
    // The plate is one hue of dust over its own smooth sky (modelled by the bake):
    // plate - back = a * hue - alpha * back. Solve for the dust's coverage, alpha;
    // the hue was measured from the plate's dust body.
    const vec3 hue = vec3(0.465, 0.312, 0.222);
    vec3 d = plate - back;
    float hh = dot(hue, hue), hb = dot(hue, back);
    float alpha = (hb * dot(hue, d) - hh * dot(back, d)) / max(hh * dot(back, back) - hb * hb, 1e-4);
    alpha = clamp((alpha - 0.04) / 0.86, 0.0, 1.0);
    // Swap the plate's sky for the scene's darkened sky.
    vec3 dust = clamp(plate - (1.0 - alpha) * back, vec3(0.0), vec3(alpha));
    fragColor = (vec4(dust, alpha) + (1.0 - alpha) * dusk) * qt_Opacity;
}
