#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
};

#extension GL_GOOGLE_include_directive : enable
#include "noise.glsl"

// The same 64-periodic corner values used by sloped(), evaluated once per lattice cell.
void main() {
    vec2 i = floor(qt_TexCoord0 * 64.0);
    fragColor = vec4(hash(i), hash(mod(i + vec2(1, 0), 64.0)),
                     hash(mod(i + vec2(0, 1), 64.0)), hash(mod(i + vec2(1, 1), 64.0)));
}
