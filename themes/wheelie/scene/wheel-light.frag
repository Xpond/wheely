#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float turn;
    float tireRadius;
    float exposure;
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec2 p = qt_TexCoord0 - 0.5;
    float angle = -6.28318530718 * turn;
    float c = cos(angle), s = sin(angle);
    // Rotate the material beneath a light field fixed in scene coordinates.
    vec2 uv = mat2(c, -s, s, c) * p + 0.5;
    vec4 tex = texture(source, uv);
    float radius = length(p) / tireRadius;
    float facing = dot(p / max(length(p), 0.0001), normalize(vec2(-0.9, -0.45)));
    float key = smoothstep(-0.2, 1.0, facing) * mix(0.4, 1.0, smoothstep(0.55, 0.9, radius));
    float shade = smoothstep(0.1, 1.0, -facing) * smoothstep(0.25, 0.8, radius);
    vec3 gain = vec3(0.93, 0.96, 1.0) + key * vec3(0.54, 0.32, 0.10)
                - shade * vec3(0.25, 0.24, 0.22);
    fragColor = vec4(min(tex.rgb * gain * exposure, vec3(tex.a)), tex.a) * qt_Opacity;
}
