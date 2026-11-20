#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float light; // 1 for the daylight variant.
    float sandFrom; // The scene row, as a share of its height, below which daylight recolours sand.
    vec4 sceneRect; // The scene's left, top, width, and height in this texture.
    vec4 crop; // The part of the source to show, as shares of it.
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

void main() {
    vec2 uv = (qt_TexCoord0 - sceneRect.xy) / sceneRect.zw; // Scene coordinates.
    vec4 color = texture(source, crop.xy + qt_TexCoord0 * crop.zw);
    if (light > 0.5 && uv.y > sandFrom) color = daylightSand(color, uv, false);
    fragColor = sceneLight(color, uv, light) * qt_Opacity;
}
