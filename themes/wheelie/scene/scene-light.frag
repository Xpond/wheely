#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 sceneRect; // The scene's left, top, width, and height in this texture.
    vec4 crop; // The part of the source to show, as shares of it.
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

void main() {
    vec2 uv = (qt_TexCoord0 - sceneRect.xy) / sceneRect.zw; // Scene coordinates.
    fragColor = sceneLight(texture(source, crop.xy + qt_TexCoord0 * crop.zw), uv) * qt_Opacity;
}
