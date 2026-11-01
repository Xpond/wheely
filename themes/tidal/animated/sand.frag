#version 440
layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec2 resolution;
};

#extension GL_GOOGLE_include_directive : enable
#include "noise.glsl"

// The sand's broad variation, which depends only on the position on the screen.
void main() {
    vec2 p = (qt_TexCoord0 - 0.5) * resolution / resolution.y;
    fragColor = vec4(noise(p * 3.0 + 9.0), 0.02 * noise(p * 5.0) + 0.015 * noise(p * 11.0 + 3.0),
                     noise(p * vec2(1.5, 3.0)), noise(p * 2.5 + 3.0));
}
