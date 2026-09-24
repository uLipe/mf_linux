#!/usr/bin/env python3
"""Cliente de linha de comando da ECU KGM (MasterFuel).

Escritas (set, cell, restore) vao para a RAM da ECU e valem na hora para o motor, mas
somem ao desligar; so viram permanentes com --burn ou com o subcomando burn.
"""
import argparse
import json
import os
import sys
import time

from channels import UNMAPPED, decode, render
from layouts import STRUCTS
from pages import PAGE_SIZES, PAGES, TABLES, Table, fields, find_field, locate, page_entities
from protocol import Ecu, EcuError, crc

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')


def read_all(ecu):
    return {p: ecu.read_page(p, PAGE_SIZES[p]) for p in PAGES}


def save_backup(ecu, pages, path=None):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    path = path or os.path.join(BACKUP_DIR, 'tune_%s.json' % time.strftime('%Y%m%d_%H%M%S'))
    with open(path, 'w') as f:
        json.dump({'signature': ecu.signature(), 'time': time.time(),
                   'pages': {p: pages[p].hex() for p in pages}}, f, indent=1)
    return path


def burn_pages(ecu, pages):
    for p in pages:
        ecu.burn(p)
        print('pagina %d gravada na flash' % p)


# ------------------------------------------------------------------ comandos

def cmd_info(ecu, a):
    ver, bf, tbf = ecu.capabilities()
    print('assinatura : %s' % ecu.signature())
    print('produto    : %s' % ecu.product())
    print('protocolo  : v%d, blocking factor %d, table blocking factor %d' % (ver, bf, tbf))
    print('burn pend. : %s' % ('sim' if ecu.burn_pending() else 'nao'))


def cmd_live(ecu, a):
    while True:
        text = render(decode(ecu.realtime()), a.all)
        if a.once:
            print(text)
            print('\nsem mapeamento: ' + ', '.join(UNMAPPED))
            return
        sys.stdout.write('\x1b[H\x1b[2J' + text + '\n')
        sys.stdout.flush()
        time.sleep(1.0 / a.hz)


def cmd_pages(ecu, a):
    for p in PAGES:
        data = ecu.read_page(p, PAGE_SIZES[p])
        d = ecu.page_crc(p)
        ents = ', '.join(name for _, name, _, _ in page_entities(p))
        print('pag %2d %3d B  crc %08X %s  %s' % (p, PAGE_SIZES[p], d,
                                                   'ok' if d == crc(data) else 'DIVERGE', ents))


def cmd_dump(ecu, a):
    print('backup em %s' % save_backup(ecu, read_all(ecu), a.output))


def cmd_restore(ecu, a):
    with open(a.file) as f:
        b = json.load(f)
    sig = ecu.signature()
    if b['signature'] != sig and not a.force:
        raise SystemExit('backup e de %r, ECU e %r (use --force)' % (b['signature'], sig))
    target = {int(p): bytes.fromhex(h) for p, h in b['pages'].items()}
    current = read_all(ecu)
    print('backup do estado atual em %s' % save_backup(ecu, current))
    touched = []
    for p in sorted(target):
        if len(target[p]) != PAGE_SIZES[p]:
            raise SystemExit('pagina %d do backup tem %d bytes' % (p, len(target[p])))
        n = ecu.write_changes(p, current[p], target[p])
        if n:
            touched.append(p)
            print('pagina %d: %d bytes restaurados' % (p, n))
    if not touched:
        print('ECU ja esta igual ao backup')
    elif a.burn:
        burn_pages(ecu, touched)


def _table(ecu, name):
    page, off, size = locate(name)
    return page, off, Table(name, ecu.read_page(page, PAGE_SIZES[page], off, size))


def cmd_table(ecu, a):
    page, off, t = _table(ecu, a.name)
    show = (lambda v: str(v)) if a.raw else (lambda v: str(t.eng(v)))
    w = max(5, max(len(show(v)) for row in t.values for v in row) + 1,
            max(len(str(x)) for x in t.rpm) + 1)
    print('%s (pagina %d) %s%s' % (t.name, page, 'cru' if a.raw else t.unit or 'cru',
                                    '' if a.raw or t.scale is not None else ' (escala depende do modo)'))
    for r in reversed(range(t.n)):
        print('%5d |%s' % (t.load[r], ''.join(show(v).rjust(w) for v in t.values[r])))
    print('      +' + '-' * (w * t.n))
    print('       ' + ''.join(str(x).rjust(w) for x in t.rpm))
    for issue in t.axis_issues():
        print('AVISO: ' + issue)


def cmd_cell(ecu, a):
    page, off, t = _table(ecu, a.name)
    if not (0 <= a.load < t.n and 0 <= a.rpm < t.n):
        raise SystemExit('indices vao de 0 a %d' % (t.n - 1))
    old = t.values[a.load][a.rpm]
    print('%s[carga %d=%d][rpm %d=%d] = %s' % (t.name, a.load, t.load[a.load], a.rpm,
                                              t.rpm[a.rpm], t.eng(old)))
    if a.value is None:
        return
    before = t.to_bytes()
    t.values[a.load][a.rpm] = t.raw(a.value)
    page_data = bytearray(ecu.read_page(page, PAGE_SIZES[page]))
    old_page = bytes(page_data)
    page_data[off:off + len(before)] = t.to_bytes()
    ecu.write_changes(page, old_page, bytes(page_data))
    print('-> %s (verificado por CRC)' % t.eng(t.values[a.load][a.rpm]))
    if a.burn:
        burn_pages(ecu, [page])


def cmd_fields(ecu, a):
    for sname in sorted({n for p in PAGES for k, n in PAGES[p] if k == 'raw'}):
        if a.struct and sname != a.struct:
            continue
        page, off, size = locate(sname)
        buf = ecu.read_page(page, PAGE_SIZES[page], off, size)
        for f in fields(sname):
            if a.filter and a.filter.lower() not in f.name.lower():
                continue
            print('%-45s = %s' % (repr(f), f.get(buf)))


def cmd_get(ecu, a):
    page, off, f = find_field(a.field)
    buf = ecu.read_page(page, PAGE_SIZES[page], off, STRUCTS[f.struct]['size'])
    print('%r = %s' % (f, f.get(buf)))


def cmd_set(ecu, a):
    page, off, f = find_field(a.field)
    value = [int(v, 0) for v in a.value.split(',')] if f.count > 1 else int(a.value, 0)
    old_page = ecu.read_page(page, PAGE_SIZES[page])
    new_page = bytearray(old_page)
    struct_buf = bytearray(old_page[off:])
    before = f.get(struct_buf)
    f.set(struct_buf, value)
    new_page[off:] = struct_buf
    ecu.write_changes(page, old_page, bytes(new_page))
    print('%r: %s -> %s (verificado por CRC)' % (f, before, f.get(struct_buf)))
    if a.burn:
        burn_pages(ecu, [page])


def cmd_burn(ecu, a):
    burn_pages(ecu, list(PAGES) if a.page == 'all' else [int(a.page)])


def cmd_toothlog(ecu, a):
    ecu.tooth_logger(True)
    try:
        time.sleep(a.wait)
        gaps = ecu.read_tooth_log()
    finally:
        ecu.tooth_logger(False)
    print(' '.join(str(g) for g in gaps))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--port', default=os.environ.get('KGM_PORT', '/dev/ttyUSB0'))
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('info', help='identidade e capacidades da ECU')

    s = sub.add_parser('live', help='canais ao vivo')
    s.add_argument('--once', action='store_true')
    s.add_argument('--all', action='store_true', help='inclui canais sem rotulo no MasterFuel')
    s.add_argument('--hz', type=float, default=5.0)

    sub.add_parser('pages', help='paginas, conteudo e CRC')

    s = sub.add_parser('dump', help='backup de todas as paginas em JSON')
    s.add_argument('-o', '--output')

    s = sub.add_parser('restore', help='restaura um backup (so o que difere)')
    s.add_argument('file')
    s.add_argument('--burn', action='store_true')
    s.add_argument('--force', action='store_true', help='ignora assinatura diferente')

    s = sub.add_parser('table', help='mostra uma tabela 3D')
    s.add_argument('name', choices=sorted(TABLES))
    s.add_argument('--raw', action='store_true')

    s = sub.add_parser('cell', help='le ou altera uma celula de tabela')
    s.add_argument('name', choices=sorted(TABLES))
    s.add_argument('load', type=int, help='indice da carga (0 = menor)')
    s.add_argument('rpm', type=int, help='indice do rpm (0 = menor)')
    s.add_argument('value', type=float, nargs='?', help='valor em unidade de engenharia')
    s.add_argument('--burn', action='store_true')

    s = sub.add_parser('fields', help='lista campos de configuracao com valores')
    s.add_argument('struct', nargs='?')
    s.add_argument('--filter')

    s = sub.add_parser('get', help='le um campo (config4.dwellRun ou dwellRun)')
    s.add_argument('field')

    s = sub.add_parser('set', help='altera um campo cru; arrays como a,b,c')
    s.add_argument('field')
    s.add_argument('value')
    s.add_argument('--burn', action='store_true')

    s = sub.add_parser('burn', help='grava pagina(s) da RAM na flash')
    s.add_argument('page', help='numero da pagina ou all')

    s = sub.add_parser('toothlog', help='captura o tooth logger')
    s.add_argument('--wait', type=float, default=1.0)

    a = ap.parse_args()
    try:
        with Ecu(a.port) as ecu:
            globals()['cmd_' + a.cmd](ecu, a)
    except EcuError as ex:
        raise SystemExit('erro: %s' % ex)


if __name__ == '__main__':
    main()
