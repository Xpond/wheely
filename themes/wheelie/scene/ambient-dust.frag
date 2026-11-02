#version 440
layout(location = 0) in vec2 uv;
layout(location = 1) in float fade;
layout(location = 2) in vec2 place;
layout(location = 0) out vec4 fragColor;
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float clock;
    float epochOffset;
    float seed;
    vec2 extent;
    float period;
    float rate;
    float lifetime;
    float variation;
    int count;
    vec4 area;
    vec4 velocity;
    vec3 sizes;
    vec4 shape;
    vec4 tint;
    vec4 force;
};
layout(binding = 1) uniform sampler2D source;

#extension GL_GOOGLE_include_directive : enable
#include "scene-light.glsl"

void main() {
    fragColor = sceneLight(texture(source, uv) * tint, place) * (fade * qt_Opacity);
}
