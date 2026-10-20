#version 440
layout(location = 0) in vec4 qt_Vertex;
layout(location = 1) in vec2 qt_MultiTexCoord0;
layout(location = 0) out vec2 uv;
layout(location = 1) out float fade;
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
};

// A full-period generator with intermediates that remain exact in 32-bit floats.
// Schrage's split also works in the GLSL 120 path selected by desktop Qt.
float random(inout float state) {
    float high = floor(state / 8216.0);
    state = 1021.0 * (state - high * 8216.0) - 57.0 * high;
    if (state <= 0.0) state += 8388593.0;
    return state / 8388593.0;
}

vec2 random2(inout float state) {
    float x = random(state);
    return vec2(x, random(state));
}

void main() {
    float row = floor(qt_MultiTexCoord0.y * float(4 * count - 3) + 0.5);
    float slot = floor((row + 1.0) / 4.0);
    float edge = mod(row, 4.0);
    uv = edge == 0.0 ? vec2(qt_MultiTexCoord0.x, 0.0)
       : edge == 1.0 ? vec2(qt_MultiTexCoord0.x, 1.0)
       : edge == 2.0 ? vec2(1.0) : vec2(0.0);

    // Stagger births at the original emission rate; reuse slots after their maximum life.
    float elapsed = clock + period - slot / rate;
    float age = mod(elapsed, period);
    float cycle = floor(elapsed / period);
    float state = mod(mod(slot + cycle * float(count) + epochOffset, 8388592.0) + seed, 8388592.0) + 1.0;
    random(state);
    float life = lifetime - variation + floor(random(state) * (2000.0 * variation + 1.0)) / 1000.0;
    vec2 origin = (area.xy + random2(state) * area.zw) * extent;
    vec2 speed = velocity.xy + (2.0 * random2(state) - 1.0) * velocity.zw;
    float offset = (2.0 * random(state) - 1.0) * sizes.z;
    float rotation = (2.0 * random(state) - 1.0) * shape.z;
    float spin = (2.0 * random(state) - 1.0) * shape.w;
    float angle = radians(rotation + spin * age);
    float t = age / life;
    float size = max(3.0, mix(max(0.0, sizes.x + offset), max(0.0, sizes.y + offset), t * t));
    fade = clamp(t * 10.0, 0.0, 1.0) * clamp((1.0 - t) * 4.0, 0.0, 1.0);
    if (age > life) size = 0.0;
    vec2 corner = (uv - 0.5) * size * shape.xy;
    float c = cos(angle), s = sin(angle);
    vec2 position = origin + age * speed + mat2(c, s, -s, c) * corner;
    gl_Position = qt_Matrix * vec4(position, 0.0, 1.0);
}
