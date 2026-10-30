#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float frame;
    vec2 grid; // Columns and rows of frames in the source.
    vec4 rect; // The chain's left, top, width, and height in the scene.
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

void main() {
    vec2 cell = vec2(mod(frame, grid.x), floor(frame / grid.x));
    vec4 tex = texture(source, (cell + qt_TexCoord0) / grid);
    vec3 color = tex.rgb / max(tex.a, 0.0001);
    fragColor = vec4(sceneLight(color, rect.xy + qt_TexCoord0 * rect.zw) * tex.a, tex.a) * qt_Opacity;
}
