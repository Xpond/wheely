#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 resolution;
};
float hash(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }

float noise(float x) { float i = floor(x), f = fract(x); return mix(hash(i), hash(i + 1.0), f * f * f * (f * (6.0 * f - 15.0) + 10.0)); }
// Surge k's reach at horizontal position u, in screen heights.
float reach(float k, float u) {
    float seed = 97.0 * hash(k + 0.4), size = 0.7 + 0.6 * hash(k + 0.8), rough = 0.6 + 0.8 * hash(k + 0.5);
    return 0.6 + 0.14 * hash(k + 0.2) + 0.09 * (noise(u * 0.8 * size + seed) - 0.5)
         + rough * (0.06 * (noise(u * 2.7 * size + seed + 3.0) - 0.5) + 0.025 * (noise(u * 7.0 * size + seed + 7.0) - 0.5));
}

// Phase delay in seconds across surge k's front.
float late(float k, float u) {
    float seed = 57.0 * hash(k + 0.9), size = 0.7 + 0.6 * hash(k + 0.7);
    return (0.8 + 0.9 * hash(k + 0.15)) * (noise(u * 1.1 * size + seed) - 0.5) + 0.35 * (noise(u * 3.3 * size + seed + 4.0) - 0.5);
}

// Three settled surges and two old tide marks, cached once per screen column.
void main() {
    float u = (qt_TexCoord0.x - 0.5) * resolution.x / resolution.y;
    float row = floor(qt_TexCoord0.y * 4.0);
    if (row > 2.5) {
        vec4 grit;
        for (int m = 0; m < 2; ++m) {
            float line = 0.25 + 0.09 * float(m) + 0.06 * (noise(u * 1.1 + 13.0 * float(m)) - 0.5)
                       + 0.03 * (noise(u * 3.5 + 41.0 + 17.0 * float(m)) - 0.5);
            float strength = smoothstep(0.2, 0.7, noise(u * 9.0 + 7.0 * float(m)));
            if (m == 0) grit.xy = vec2(line, strength);
            else grit.zw = vec2(line, strength);
        }
        fragColor = grit;
        return;
    }
    float k = 24.0 - row;
    float start = k * 6.0 + 1.8 * hash(k + 0.1) + 1.6 * (hash(k + 0.3) - 0.5) * u + late(k, u);
    fragColor = vec4(start, reach(k, u), noise(u * 6.0 + k), noise(u * 90.0 + k));
}
