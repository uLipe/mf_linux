#version 440
// Gauge radial inteiro num quad: arco, faixas de alerta e marcas saem de distancias
// analiticas, entao mudar o valor so troca um uniform -- nada e retesselado na CPU.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    vec4 trackColor;
    vec4 valueColor;
    vec4 warnColor;
    vec4 dangerColor;
    vec4 tickColor;
    float frac;
    float warnFrac;
    float dangerFrac;
    float thickness;
    float ticks;
    float px;
};

const float PI = 3.14159265;
const float START = 0.75 * PI;
const float SWEEP = 1.5 * PI;

vec4 over(vec4 dst, vec4 src, float a)
{
    src.a *= a;
    return vec4(src.rgb * src.a + dst.rgb * (1.0 - src.a), src.a + dst.a * (1.0 - src.a));
}

float band(float lo, float hi, float d)
{
    return smoothstep(lo - px, lo + px, d) * (1.0 - smoothstep(hi - px, hi + px, d));
}

void main()
{
    vec2 p = qt_TexCoord0 * 2.0 - 1.0;
    float r = length(p);
    float t = mod(atan(p.y, p.x) - START + 2.0 * PI, 2.0 * PI) / SWEEP;
    // Divide o vao inferior ao meio para que os dois extremos tenham borda suave.
    if (t > 1.0 + (2.0 * PI / SWEEP - 1.0) * 0.5)
        t -= 2.0 * PI / SWEEP;
    float arc = t * SWEEP * r;

    float outer = 1.0 - 0.55 * thickness - 2.0 * px;
    float inner = outer - thickness;
    float ring = band(inner, outer, r);
    float inSweep = band(0.0, SWEEP * r, arc);

    vec4 c = vec4(0.0);
    c = over(c, trackColor, ring * inSweep);
    c = over(c, valueColor, ring * band(0.0, frac * SWEEP * r, arc));

    float zone = band(1.0 - 0.38 * thickness - px, 1.0 - px, r);
    float warnEnd = min(dangerFrac, 1.0);
    c = over(c, warnColor, zone * band(warnFrac * SWEEP * r, warnEnd * SWEEP * r, arc));
    c = over(c, dangerColor, zone * band(dangerFrac * SWEEP * r, SWEEP * r, arc));

    float cell = t * ticks;
    float tickDist = abs(cell - floor(cell + 0.5)) / ticks * SWEEP * r;
    float tick = band(inner - 0.12, inner - 0.04, r) * (1.0 - smoothstep(0.008, 0.008 + 2.0 * px, tickDist));
    c = over(c, tickColor, tick * step(-0.001, t) * step(t, 1.001));

    fragColor = c * qt_Opacity;
}
