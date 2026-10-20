#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 sceneRect; // The scene's left, top, width, and height in this texture.
};
layout(binding = 1) uniform sampler2D source;

void main() {
    vec4 tex = texture(source, qt_TexCoord0);
    vec2 uv = (qt_TexCoord0 - sceneRect.xy) / sceneRect.zw; // Scene coordinates.
    vec3 color = tex.rgb / max(tex.a, 0.0001);
    float luma = dot(color, vec3(0.2126, 0.7152, 0.0722));
    // Retain the blue sky while warming sunlit sand, paint, cloth, and metal.
    float sky = (1.0 - smoothstep(0.55, 0.70, uv.y))
                * smoothstep(0.015, 0.12, color.b - color.r);
    float ground = smoothstep(0.67, 0.82, uv.y);
    float warm = smoothstep(0.25, 0.85, luma) * (1.0 - 0.8 * sky) * (1.0 - 0.85 * ground)
                 * (1.0 - 0.75 * smoothstep(0.82, 1.0, luma));
    float cool = 1.0 - smoothstep(0.12, 0.55, luma) + 0.35 * ground;
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
    fragColor = vec4(clamp(color, 0.0, 1.0) * tex.a, tex.a) * qt_Opacity;
}
