#version 440
// Gauge inteiro desenhado aqui: o valor chega como uniform, entao animar o ponteiro nao
// reconstroi geometria nem retessela curvas -- a CPU so atualiza um float por frame.

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float value;      // 0..1 ao longo do arco
    float warnFrom;   // 0..1 inicio da faixa de alerta; >= 1 desliga
    float marker;     // 0..1 marcador de alvo; < 0 desliga
    float thickness;  // espessura do arco em fracao do raio
    float ticks;      // divisoes da escala
    vec4 trackColor;
    vec4 fillColor;
    vec4 warnColor;
    vec4 markerColor;
    vec4 tickColor;
};

const float PI = 3.14159265;
const float SWEEP = 1.5 * PI;          // 270 graus, abertura embaixo
const float OUTER = 0.97;

vec4 over(vec4 dst, vec4 src, float m)
{
    float a = src.a * m;
    return vec4(src.rgb * a, a) + dst * (1.0 - a);
}

float band(float x, float lo, float hi, float aa)
{
    return smoothstep(lo - aa, lo + aa, x) * (1.0 - smoothstep(hi - aa, hi + aa, x));
}

void main()
{
    vec2 p = qt_TexCoord0 * 2.0 - 1.0;
    p.y = -p.y;
    float r = length(p);
    float t = (atan(p.x, p.y) + 0.5 * SWEEP) / SWEEP;   // 0 = inicio (baixo-esq), 1 = fim
    float aa = fwidth(r);
    float aat = fwidth(t);

    // distancia em comprimento de arco ate as pontas, para suavizar os extremos
    float ends = smoothstep(-aa, aa, min(t, 1.0 - t) * SWEEP * r);
    float inner = OUTER - thickness;
    float ring = band(r, inner, OUTER, aa) * ends;

    float warn = smoothstep(warnFrom - aat, warnFrom + aat, t);
    vec4 track = mix(trackColor, mix(trackColor, warnColor, 0.28), warn);
    vec4 lit = mix(fillColor, warnColor, warn);
    float filled = 1.0 - smoothstep(value - aat, value + aat, t);
    vec4 c = over(vec4(0.0), mix(track, lit, filled), ring);

    float along = abs(fract(t * ticks + 0.5) - 0.5) / ticks * SWEEP * r;
    float tickEnds = step(-0.5 / ticks, t) * step(t, 1.0 + 0.5 / ticks);
    float tick = band(r, inner - 0.11, inner - 0.04, aa)
               * (1.0 - smoothstep(0.008 - aa, 0.008 + aa, along)) * tickEnds;
    c = over(c, tickColor, tick);

    float dm = abs(t - marker) * SWEEP * r;
    float mk = step(0.0, marker) * band(r, inner - 0.05, OUTER + 0.02, aa)
             * (1.0 - smoothstep(0.012 - aa, 0.012 + aa, dm));
    c = over(c, markerColor, mk);

    fragColor = c * qt_Opacity;
}
