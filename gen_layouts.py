#!/usr/bin/env python3
"""Gera layouts.py com o layout exato dos structs de configuracao, lido do DWARF do ELF.

Rodar de novo sempre que o firmware mudar um struct configN: o layout vem do binario
compilado, entao nao ha como divergir do que a ECU realmente usa.

    python3 gen_layouts.py ../kgm-firmware/build/firmware-debug/firmware.elf
"""
import os
import re
import shutil
import subprocess
import sys

STRUCTS = ['config2', 'config4', 'config6', 'config9', 'config10', 'config13', 'config15']

GDB_CANDIDATES = [
    os.environ.get('GDB'),
    '/opt/st/stm32cubeide_1.19.0/plugins/com.st.stm32cube.ide.mcu.externaltools.'
    'gnu-tools-for-stm32.13.3.rel1.linux64_1.0.0.202410170706/tools/bin/arm-none-eabi-gdb',
    shutil.which('arm-none-eabi-gdb'),
    shutil.which('gdb-multiarch'),
]

# /*   36: 4   |       1 */    uint8_t nCylinders : 4;
# /*   28      |       8 */    uint16_t injAng[4];
LINE = re.compile(
    r'/\*\s*(\d+)(?::\s*(\d+))?\s*\|\s*(\d+)\s*\*/\s+(.+?)\s+(\w+)((?:\[\d+\])*)(?:\s*:\s*(\d+))?;')
TOTAL = re.compile(r'total size \(bytes\):\s*(\d+)')


def find_gdb():
    for g in GDB_CANDIDATES:
        if g and os.path.isfile(g) and os.access(g, os.X_OK):
            return g
    sys.exit('arm-none-eabi-gdb nao encontrado; defina GDB=/caminho/para/gdb')


def ptype(gdb, elf, struct):
    out = subprocess.run(
        [gdb, '-batch', '-nx', '-ex', 'set width 0', '-ex', 'set pagination off',
         '-ex', 'ptype /o struct %s' % struct, elf],
        capture_output=True, text=True, check=True).stdout
    fields = []
    for line in out.splitlines():
        m = LINE.search(line)
        if not m:
            continue
        off, bit, size, ctype, name, dims, bits = m.groups()
        count = 1
        for d in re.findall(r'\[(\d+)\]', dims):
            count *= int(d)
        signed = ctype.strip().startswith('int') or ctype.strip() in ('char', 'signed char')
        fields.append((name, int(off), int(bit or 0), int(bits) if bits else 0,
                       int(size), signed, count, ctype.strip()))
    m = TOTAL.search(out)
    if not m:
        sys.exit('struct %s nao encontrado no ELF (build sem -g?)' % struct)
    return int(m.group(1)), fields


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    elf = sys.argv[1]
    gdb = find_gdb()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'layouts.py'), 'w', newline='\n') as o:
        o.write('"""GERADO por gen_layouts.py a partir de %s -- nao editar a mao.\n\n'
                % os.path.basename(elf))
        o.write('Campo: (nome, offset, bit, bits, size, signed, count, ctype).\n'
                'bits == 0 -> campo inteiro; size e o total (count elementos de size/count bytes).\n"""\n\n')
        o.write('STRUCTS = {\n')
        for s in STRUCTS:
            total, fields = ptype(gdb, elf, s)
            o.write('    %r: {\n        \'size\': %d,\n        \'fields\': [\n' % (s, total))
            for f in fields:
                o.write('            %r,\n' % (f,))
            o.write('        ],\n    },\n')
            print('%-9s %4d bytes, %3d campos' % (s, total, len(fields)))
        o.write('}\n')


if __name__ == '__main__':
    main()
