"""Modelo das paginas de configuracao (speeduino_core/pages.cpp).

Uma pagina e uma sequencia de entidades: tabela 3D ou bloco raw (struct configN).
Tabela na pagina: valores N*N em ordem cartesiana (linha 0 = menor carga), depois o
eixo X (RPM) e o eixo Y (carga), ambos crescentes e convertidos para 1 byte.
"""
import struct

from layouts import STRUCTS

# pages.cpp:27
PAGE_SIZES = [0, 128, 288, 288, 128, 288, 128, 240, 384, 192, 192, 288, 192, 128, 288, 256]

# table3d_axis_io.cpp: RPM /100, carga /2 (TPS 1:1 existe mas nenhuma tabela usa).
AXIS_SCALE = {'rpm': 100, 'load': 2}

# (tamanho, escala, soma, unidade) do valor. Escala None = significado depende do modo
# configurado (ex.: boost e alvo em kPa ou duty); expor o byte cru.
TABLES = {
    've':          (16, 1,    0,    '%'),
    've2':         (16, 1,    0,    '%'),
    'ign':         (16, 1,    -40,  'deg'),      # OFFSET_IGNITION
    'ign2':        (16, 1,    -40,  'deg'),
    'afr':         (16, 0.1,  0,    'AFR'),
    'boost':       (8,  None, 0,    ''),         # x2: kPa (malha fechada) ou % (aberta)
    'vvt':         (8,  None, 0,    ''),         # duty ou angulo, conforme vvtMode
    'staging':     (8,  1,    0,    '%'),
    'trim1':       (6,  1,    -127, '%'),        # OFFSET_FUELTRIM
    'trim2':       (6,  1,    -127, '%'),
    'trim3':       (6,  1,    -127, '%'),
    'trim4':       (6,  1,    -127, '%'),
    'trim5':       (6,  1,    -127, '%'),
    'trim6':       (6,  1,    -127, '%'),
    'trim7':       (6,  1,    -127, '%'),
    'trim8':       (6,  1,    -127, '%'),
    'wmi':         (8,  None, 0,    ''),
    'vvt2':        (8,  None, 0,    ''),
    'dwell':       (4,  0.1,  0,    'ms'),       # x100 us em speeduino_core.cpp:1806
    'boostLookup': (8,  0.5,  0,    '%'),        # *100/2 em auxiliaries.cpp:736
}

# pages.cpp map_page_offset_to_entity. ('table', nome) | ('raw', struct); o resto da pagina e padding.
PAGES = {
    1:  [('raw', 'config2')],
    2:  [('table', 've')],
    3:  [('table', 'ign')],
    4:  [('raw', 'config4')],
    5:  [('table', 'afr')],
    6:  [('raw', 'config6')],
    7:  [('table', 'boost'), ('table', 'vvt'), ('table', 'staging')],
    8:  [('table', 'trim%d' % i) for i in range(1, 9)],
    9:  [('raw', 'config9')],
    10: [('raw', 'config10')],
    11: [('table', 've2')],
    12: [('table', 'wmi'), ('table', 'vvt2'), ('table', 'dwell')],
    13: [('raw', 'config13')],
    14: [('table', 'ign2')],
    15: [('table', 'boostLookup'), ('raw', 'config15')],
}


def entity_size(kind, name):
    if kind == 'table':
        n = TABLES[name][0]
        return n * n + 2 * n
    return STRUCTS[name]['size']


def page_entities(page):
    """[(kind, nome, offset, tamanho)] com offset dentro da pagina."""
    out, off = [], 0
    for kind, name in PAGES[page]:
        size = entity_size(kind, name)
        out.append((kind, name, off, size))
        off += size
    if off > PAGE_SIZES[page]:
        raise AssertionError('pagina %d: entidades somam %d > %d' % (page, off, PAGE_SIZES[page]))
    return out


def locate(name):
    """(pagina, offset, tamanho) de uma tabela ou struct pelo nome."""
    for page in PAGES:
        for kind, n, off, size in page_entities(page):
            if n == name:
                return page, off, size
    raise KeyError(name)


# ------------------------------------------------------------------ tabelas

class Table:
    def __init__(self, name, raw):
        self.name = name
        self.n, self.scale, self.add, self.unit = TABLES[name]
        n = self.n
        if len(raw) != n * n + 2 * n:
            raise ValueError('%s: %d bytes, esperado %d' % (name, len(raw), n * n + 2 * n))
        self.values = [list(raw[r * n:(r + 1) * n]) for r in range(n)]   # [carga][rpm]
        self.rpm = [b * AXIS_SCALE['rpm'] for b in raw[n * n:n * n + n]]
        self.load = [b * AXIS_SCALE['load'] for b in raw[n * n + n:]]

    def to_bytes(self):
        n = self.n
        out = bytearray()
        for row in self.values:
            out += bytes(row)
        for v in self.rpm:
            out.append(_axis_byte(v, 'rpm'))
        for v in self.load:
            out.append(_axis_byte(v, 'load'))
        return bytes(out)

    def axis_issues(self):
        """A interpolacao (table3d_interpolate.cpp) assume eixos estritamente crescentes."""
        out = []
        for label, axis in (('rpm', self.rpm), ('load', self.load)):
            for i in range(1, len(axis)):
                if axis[i] <= axis[i - 1]:
                    out.append('%s: eixo %s[%d]=%d nao e maior que [%d]=%d'
                               % (self.name, label, i, axis[i], i - 1, axis[i - 1]))
        return out

    def eng(self, raw):
        return raw if self.scale is None else round(raw * self.scale + self.add, 3)

    def raw(self, eng):
        if self.scale is None:
            v = int(round(eng))
        else:
            v = int(round((eng - self.add) / self.scale))
        if not 0 <= v <= 255:
            raise ValueError('%s: %r fora do byte (0..255 cru)' % (self.name, eng))
        return v


def _axis_byte(value, domain):
    s = AXIS_SCALE[domain]
    if value % s:
        raise ValueError('eixo %s: %d nao e multiplo de %d' % (domain, value, s))
    b = value // s
    if not 0 <= b <= 255:
        raise ValueError('eixo %s: %d fora da faixa' % (domain, value))
    return b


# ------------------------------------------------------------------- campos

class Field:
    def __init__(self, struct_name, spec):
        self.struct = struct_name
        (self.name, self.offset, self.bit, self.bits, self.size,
         self.signed, self.count, self.ctype) = spec
        self.elem = self.size // self.count

    def __repr__(self):
        where = '%d:%d/%d' % (self.offset, self.bit, self.bits) if self.bits else '%d' % self.offset
        dims = '[%d]' % self.count if self.count > 1 else ''
        return '%s.%s%s @%s (%s)' % (self.struct, self.name, dims, where, self.ctype)

    def get(self, buf):
        if self.bits:
            nbytes = (self.bit + self.bits + 7) // 8
            word = int.from_bytes(buf[self.offset:self.offset + nbytes], 'little')
            v = (word >> self.bit) & ((1 << self.bits) - 1)
            return v - (1 << self.bits) if self.signed and v >> (self.bits - 1) else v
        vals = [int.from_bytes(buf[self.offset + i * self.elem:self.offset + (i + 1) * self.elem],
                               'little', signed=self.signed) for i in range(self.count)]
        return vals if self.count > 1 else vals[0]

    def set(self, buf, value):
        """Grava value em buf (bytearray) e devolve o intervalo de bytes alterado."""
        if self.bits:
            lo, hi = -(1 << (self.bits - 1)) if self.signed else 0, \
                (1 << (self.bits - 1)) - 1 if self.signed else (1 << self.bits) - 1
            if not lo <= value <= hi:
                raise ValueError('%s: %d fora de %d..%d' % (self.name, value, lo, hi))
            nbytes = (self.bit + self.bits + 7) // 8
            mask = ((1 << self.bits) - 1) << self.bit
            word = int.from_bytes(buf[self.offset:self.offset + nbytes], 'little')
            word = (word & ~mask) | ((value << self.bit) & mask)
            buf[self.offset:self.offset + nbytes] = word.to_bytes(nbytes, 'little')
            return self.offset, nbytes
        vals = value if self.count > 1 else [value]
        if len(vals) != self.count:
            raise ValueError('%s: esperados %d elementos' % (self.name, self.count))
        for i, v in enumerate(vals):
            a = self.offset + i * self.elem
            buf[a:a + self.elem] = int(v).to_bytes(self.elem, 'little', signed=self.signed)
        return self.offset, self.size


def fields(struct_name):
    return [Field(struct_name, spec) for spec in STRUCTS[struct_name]['fields']]


def find_field(qualified):
    """'config2.nCylinders' ou so 'nCylinders' (se unico). Devolve (pagina, offset do struct, Field)."""
    if '.' in qualified:
        sname, fname = qualified.split('.', 1)
        candidates = [(sname, f) for f in fields(sname) if f.name == fname]
    else:
        candidates = [(s, f) for s in STRUCTS for f in fields(s) if f.name == qualified]
    if not candidates:
        raise KeyError('campo %r nao existe' % qualified)
    if len(candidates) > 1:
        raise KeyError('%r ambiguo: %s' % (qualified, ', '.join('%s.%s' % (s, f.name)
                                                                 for s, f in candidates)))
    sname, f = candidates[0]
    page, off, _ = locate(sname)
    return page, off, f
