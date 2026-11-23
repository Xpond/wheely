#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float light; // 1 for the daylight variant.
    vec3 rows; // The pink and amber prints' tops and the sky's bottom, as shares of the scene's height.
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

// The scene's base; in daylight its sky prints turn bright sky blue, lilac, and soft aqua.
void main() {
    vec4 color = texture(source, qt_TexCoord0);
    if (light > 0.5 && qt_TexCoord0.y < rows.z) {
        vec3 hsl = rgbToHsl(color.rgb);
        // Each print's own hue, the hue it moves to with half its spread, a lightness gamma, which
        // keeps black black and white white, and a share of its saturation.
        vec4 grade = qt_TexCoord0.y < rows.x ? vec4(218.0, 204.0, 0.6, 1.0) : qt_TexCoord0.y < rows.y ? vec4(330.0, 268.0, 0.72, 0.8)
                                                                               : vec4(29.0, 176.0, 0.6, 0.45);
        float spread = fract(hsl.x - grade.x / 360.0 + 0.5) - 0.5;
        hsl.x = fract(grade.y / 360.0 + 0.5 * spread);
        hsl.z = pow(hsl.z, grade.z);
        hsl.y *= grade.w;
        color.rgb = hslToRgb(hsl);
    }
    fragColor = color * qt_Opacity;
}
