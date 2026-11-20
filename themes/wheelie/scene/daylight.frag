#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float light; // 1 for the daylight variant.
    vec4 rect; // The image's left, top, width, and height in the scene.
    vec3 rows; // The pink and amber prints' tops and the sky's bottom, as shares of the scene's height; 0 for no sky.
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

// A still image; in daylight the sky prints turn bright sky blue, coral, and lemon gold, and the sand peach.
void main() {
    vec4 color = texture(source, qt_TexCoord0);
    vec2 uv = rect.xy + qt_TexCoord0 * rect.zw;
    if (light > 0.5 && uv.y < rows.z) {
        vec3 hsl = rgbToHsl(color.rgb);
        // Each print's own hue, the hue it moves to with half its spread, and a lightness gamma,
        // which keeps black black and white white.
        vec3 grade = uv.y < rows.x ? vec3(218.0, 204.0, 0.6) : uv.y < rows.y ? vec3(330.0, 12.0, 0.72) : vec3(29.0, 44.0, 0.6);
        float spread = fract(hsl.x - grade.x / 360.0 + 0.5) - 0.5;
        hsl.x = fract(grade.y / 360.0 + 0.5 * spread);
        hsl.z = pow(hsl.z, grade.z);
        color.rgb = hslToRgb(hsl);
    } else if (light > 0.5) {
        color = daylightSand(color, uv, false);
    }
    fragColor = color * qt_Opacity;
}
