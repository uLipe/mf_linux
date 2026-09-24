"""Ponte entre a ECU e o QML: thread de leitura e o objeto exposto como `live`."""
import queue
import time

import serial
from PySide6.QtCore import (Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt,
                            QThread, QTimer, Signal, Slot)
from PySide6.QtGui import QOffscreenSurface, QOpenGLContext, QVector3D
from PySide6.QtGraphs import QSurfaceDataItem

from channels import CHANNELS, decode
from config_panels import KGM, PANELS, resolve
from pages import PAGE_SIZES, TABLES, Table, locate
from protocol import Ecu, EcuError

# Texto a 10 Hz: numero trocando a 30 Hz fica ilegivel; os gauges continuam na taxa cheia.
TEXT_EVERY = 3


def renderer_name(api):
    if api != 'opengl':
        return api
    ctx, surf = QOpenGLContext(), QOffscreenSurface()
    surf.create()
    if not (ctx.create() and ctx.makeCurrent(surf)):
        return 'opengl'
    name = ctx.functions().glGetString(0x1F01)   # GL_RENDERER
    ctx.doneCurrent()
    return 'OpenGL - %s' % name


class EcuWorker(QThread):
    """Dona exclusiva da porta serial; reconecta sozinha se a ECU some. Comandos da GUI
    entram por fila e rodam entre duas leituras ao vivo."""
    frame = Signal('QVariantMap')
    link = Signal(bool, str)
    tableLoaded = Signal(str, bytes)
    tableWritten = Signal(str, bool, str)
    pageLoaded = Signal(int, bytes)
    pageWritten = Signal(int, bool, str)
    burned = Signal(int, bool, str)

    def __init__(self, port, hz):
        super().__init__()
        self.port = port
        self.period = 1.0 / hz
        self._jobs = queue.Queue()
        self._pages = {}

    def load_table(self, name):
        self._jobs.put(('load', name, None))

    def write_table(self, name, data):
        self._jobs.put(('write', name, bytes(data)))

    def load_page(self, page):
        self._jobs.put(('loadpage', page, None))

    def patch_page(self, page, offset, data):
        self._jobs.put(('patch', page, (offset, bytes(data))))

    def burn_page(self, page):
        self._jobs.put(('burn', page, None))

    def run(self):
        while not self.isInterruptionRequested():
            try:
                with Ecu(self.port, timeout=0.5) as ecu:
                    self._pages.clear()
                    self.link.emit(True, ecu.signature())
                    self._poll(ecu)
            except (serial.SerialException, EcuError, OSError) as ex:
                self.link.emit(False, str(ex))
                self.msleep(1000)

    def _run_jobs(self, ecu):
        jobs = []
        while True:
            try:
                jobs.append(self._jobs.get_nowait())
            except queue.Empty:
                break
        # Tecla segurada gera uma rajada de escritas da mesma tabela; so o ultimo estado
        # importa, entao cada tabela e escrita uma vez por rodada.
        latest = {name: data for kind, name, data in jobs if kind == 'write'}
        patches = {}
        for kind, page, patch in jobs:
            if kind == 'patch':
                patches.setdefault(page, []).append(patch)
        for kind, arg, _ in jobs:
            try:
                if kind == 'load':
                    page, off, size = locate(arg)
                    self._pages[page] = ecu.read_page(page, PAGE_SIZES[page])
                    self.tableLoaded.emit(arg, self._pages[page][off:off + size])
                elif kind == 'loadpage':
                    self._pages[arg] = ecu.read_page(arg, PAGE_SIZES[arg])
                    self.pageLoaded.emit(arg, self._pages[arg])
                elif kind == 'write' and arg in latest:
                    self._write(ecu, arg, latest.pop(arg))
                elif kind == 'patch' and arg in patches:
                    self._patch(ecu, arg, patches.pop(arg))
                elif kind == 'burn':
                    ecu.burn(arg)
                    self.burned.emit(arg, True, '')
            except EcuError as ex:
                if kind == 'burn':
                    self.burned.emit(arg, False, str(ex))
                elif kind in ('loadpage', 'patch'):
                    self._pages.pop(arg, None)
                    self.pageWritten.emit(arg, False, str(ex))
                else:
                    self._pages.pop(locate(arg)[0], None)
                    self.tableWritten.emit(arg, False, str(ex))

    def _write(self, ecu, name, data):
        page, off, size = locate(name)
        old = self._pages.get(page) or ecu.read_page(page, PAGE_SIZES[page])
        new = old[:off] + data + old[off + size:]
        n = ecu.write_changes(page, old, new)
        self._pages[page] = new
        self.tableWritten.emit(name, True, '%d bytes, CRC ok' % n)

    def _patch(self, ecu, page, patches):
        old = self._pages.get(page) or ecu.read_page(page, PAGE_SIZES[page])
        new = bytearray(old)
        for off, data in patches:
            new[off:off + len(data)] = data
        n = ecu.write_changes(page, old, bytes(new))
        self._pages[page] = bytes(new)
        self.pageWritten.emit(page, True, '%d bytes, CRC ok' % n)

    def _poll(self, ecu):
        due = time.monotonic()
        failures = 0
        while not self.isInterruptionRequested():
            self._run_jobs(ecu)
            try:
                entry = ecu.realtime()
                failures = 0
            except EcuError:
                # Um frame perdido nao justifica reabrir a porta; tres seguidos, sim.
                failures += 1
                if failures >= 3:
                    raise
                continue
            values = {k: v[1] for k, v in decode(entry).items()}
            values['_t'] = time.monotonic()
            self.frame.emit(values)
            due += self.period
            wait = due - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            else:
                due = time.monotonic()


def _decimals(scale):
    return 0 if float(scale).is_integer() else len(repr(float(scale)).split('.')[1])


class Live(QObject):
    frameChanged = Signal()
    textChanged = Signal()
    linkChanged = Signal()
    statsChanged = Signal()

    def __init__(self, renderer):
        super().__init__()
        self._v, self._vt = {}, {}
        self._connected, self._signature, self._error = False, '', ''
        self._renderer = renderer
        self._frames = self._swaps = 0
        self._poll_hz = self._fps = 0.0
        self._t0 = None
        self._channels = [{'key': k, 'label': label or '', 'unit': unit, 'decimals': _decimals(scale)}
                          for k, label, _off, _typ, scale, _add, unit in CHANNELS]
        self._stats = QTimer(self, interval=1000, timeout=self._update_stats)
        self._stats.start()

    def watch_window(self, window):
        window.frameSwapped.connect(self._on_swap)

    @Slot()
    def _on_swap(self):
        self._swaps += 1

    def _update_stats(self):
        self._poll_hz, self._fps = float(self._frames), float(self._swaps)
        self._frames = self._swaps = 0
        self.statsChanged.emit()

    @Slot('QVariantMap')
    def on_frame(self, values):
        if self._t0 is None:
            self._t0 = values['_t']
        values['_t'] -= self._t0
        self._v = values
        self._frames += 1
        self.frameChanged.emit()
        if self._frames % TEXT_EVERY == 1:
            self._vt = values
            self.textChanged.emit()

    @Slot(bool, str)
    def on_link(self, ok, info):
        self._connected = ok
        if ok:
            self._signature, self._error = info, ''
        else:
            self._error = info
        self.linkChanged.emit()

    v = Property('QVariantMap', lambda s: s._v, notify=frameChanged)
    vt = Property('QVariantMap', lambda s: s._vt, notify=textChanged)
    connected = Property(bool, lambda s: s._connected, notify=linkChanged)
    signature = Property(str, lambda s: s._signature, notify=linkChanged)
    error = Property(str, lambda s: s._error, notify=linkChanged)
    pollHz = Property(float, lambda s: s._poll_hz, notify=statsChanged)
    fps = Property(float, lambda s: s._fps, notify=statsChanged)
    renderer = Property(str, lambda s: s._renderer, constant=True)
    channels = Property('QVariantList', lambda s: s._channels, constant=True)


TABLE_GROUPS = [
    ('Combustível', [('ve', 'VE'), ('ve2', 'VE 2'), ('afr', 'Alvo AFR'), ('staging', 'Staging')]),
    ('Ignição', [('ign', 'Avanço'), ('ign2', 'Avanço 2'), ('dwell', 'Dwell')]),
    ('Trim por cilindro', [('trim%d' % i, 'Trim cil. %d' % i) for i in range(1, 9)]),
    ('Boost / VVT', [('boost', 'Boost'), ('boostLookup', 'Boost duty'), ('vvt', 'VVT'),
                     ('vvt2', 'VVT 2'), ('wmi', 'WMI')]),
]
TABLE_LABELS = {name: label for _, items in TABLE_GROUPS for name, label in items}

# Carga que a ECU usa no lookup de cada tabela (speeduino_core.cpp getVE1/getAdvance1,
# corrections.cpp afrTarget). As demais dependem de modo configurado: sem cursor.
TABLE_LOAD = {'ve': 'fuelLoad', 'afr': 'fuelLoad', 'staging': 'fuelLoad', 'ign': 'ignLoad',
              'dwell': 'ignLoad', **{'trim%d' % i: 'fuelLoad' for i in range(1, 9)}}


def axis_position(axis, x):
    """Posicao fracionaria de x no eixo, como a interpolacao faz; None se o eixo e lixo."""
    n = len(axis)
    if x <= axis[0]:
        return 0.0
    if x >= axis[-1]:
        return float(n - 1)
    for i in range(n - 1):
        if axis[i] <= x <= axis[i + 1] and axis[i + 1] > axis[i]:
            return i + (x - axis[i]) / (axis[i + 1] - axis[i])
    return None


class CellModel(QAbstractListModel):
    """Celulas em ordem de exibicao: linha 0 no topo = maior carga."""
    TextRole, NormRole, SelectedRole, ChangedRole = range(Qt.UserRole + 1, Qt.UserRole + 5)

    def __init__(self, editor):
        super().__init__()
        self.ed = editor

    def rowCount(self, parent=QModelIndex()):
        t = self.ed.table
        return 0 if parent.isValid() or t is None else t.n * t.n

    def roleNames(self):
        return {self.TextRole: QByteArray(b'text'), self.NormRole: QByteArray(b'norm'),
                self.SelectedRole: QByteArray(b'selected'), self.ChangedRole: QByteArray(b'changed')}

    def data(self, index, role):
        ed = self.ed
        dr, c = divmod(index.row(), ed.table.n)
        r = ed.table.n - 1 - dr
        if role == self.TextRole:
            return ed.fmt(ed.table.eng(ed.table.values[r][c]))
        if role == self.NormRole:
            lo, hi = ed.range
            return 0.5 if hi == lo else (ed.table.values[r][c] - lo) / (hi - lo)
        if role == self.SelectedRole:
            return ed.in_selection(dr, c)
        if role == self.ChangedRole:
            base = ed.baseline.get(ed.name)
            return base is not None and base[r][c] != ed.table.values[r][c]
        return None

    def refresh(self, roles=None):
        if self.rowCount():
            self.dataChanged.emit(self.index(0), self.index(self.rowCount() - 1), roles or [])

    def reset(self):
        self.beginResetModel()
        self.endResetModel()


class TableEditor(QObject):
    tableChanged = Signal()
    cellsChanged = Signal()
    selectionChanged = Signal()
    statusChanged = Signal()
    cursorChanged = Signal()

    def __init__(self, worker, live):
        super().__init__()
        self.worker, self.live = worker, live
        self.table, self.name = None, ''
        self.baseline = {}                  # valores da ultima leitura/burn: o que esta na flash
        self.range = (0, 255)
        self._model = CellModel(self)
        self._undo = []
        self._anchor = self._cur = (0, 0)
        self._status, self._dirty = '', set()
        self._cursor = (-1.0, -1.0)
        worker.tableLoaded.connect(self._on_loaded)
        worker.tableWritten.connect(self._on_written)
        worker.burned.connect(self._on_burned)
        live.frameChanged.connect(self._on_frame)
        live.linkChanged.connect(self._on_link)

    # ------------------------------------------------------------ utilidades

    def fmt(self, v):
        return '%.*f' % (self._decimals(), v)

    def _decimals(self):
        s = self.table.scale if self.table else 1
        return 0 if s is None or float(s).is_integer() else 1

    def _step(self):
        s = self.table.scale
        return 1 if s is None else s

    def in_selection(self, dr, c):
        (a, b), (x, y) = self._anchor, self._cur
        return min(a, x) <= dr <= max(a, x) and min(b, y) <= c <= max(b, y)

    def _selected(self):
        n = self.table.n
        return [(n - 1 - dr, c) for dr in range(n) for c in range(n) if self.in_selection(dr, c)]

    def _set_status(self, text):
        self._status = text
        self.statusChanged.emit()

    def _update_range(self):
        flat = [v for row in self.table.values for v in row]
        self.range = (min(flat), max(flat))

    # ------------------------------------------------------------ ECU -> GUI

    @Slot(str, bytes)
    def _on_loaded(self, name, data):
        if name != self.name:
            return
        self.table = Table(name, data)
        self.baseline.setdefault(name, [row[:] for row in self.table.values])
        self._undo.clear()
        self._anchor = self._cur = (0, 0)
        self._update_range()
        self._model.reset()
        issues = self.table.axis_issues()
        self._set_status('eixo inválido: ' + issues[0] if issues else 'lida da ECU')
        self.tableChanged.emit()
        self.cellsChanged.emit()
        self.selectionChanged.emit()

    @Slot(str, bool, str)
    def _on_written(self, name, ok, info):
        if ok:
            self._dirty.add(locate(name)[0])
            self._set_status('RAM atualizada (%s) — não gravado na flash' % info)
        else:
            self._set_status('falha na escrita: %s — relendo' % info)
            if name == self.name:
                self.worker.load_table(name)
        self.tableChanged.emit()

    @Slot(int, bool, str)
    def _on_burned(self, page, ok, info):
        if not ok:
            self._set_status('falha no burn: ' + info)
            return
        self._dirty.discard(page)
        for n in TABLES:
            if locate(n)[0] == page and n == self.name and self.table:
                self.baseline[n] = [row[:] for row in self.table.values]
            elif locate(n)[0] == page:
                self.baseline.pop(n, None)
        self._model.refresh([CellModel.ChangedRole])
        self._set_status('gravado na flash')
        self.tableChanged.emit()

    @Slot()
    def _on_link(self):
        if self.live.connected and self.name:
            self.worker.load_table(self.name)

    @Slot()
    def _on_frame(self):
        pos = (-1.0, -1.0)
        key = TABLE_LOAD.get(self.name)
        v = self.live._v
        if self.table and key and key in v:
            fx = axis_position(self.table.rpm, v['rpm'])
            fy = axis_position(self.table.load, v[key])
            if fx is not None and fy is not None:
                pos = (fx, self.table.n - 1 - fy)
        if pos != self._cursor:
            self._cursor = pos
            self.cursorChanged.emit()

    # ------------------------------------------------------------ GUI -> ECU

    @Slot(str)
    def open(self, name):
        self.name = name
        self.table = None
        self._model.reset()
        self._set_status('lendo...')
        self.tableChanged.emit()
        self.worker.load_table(name)

    @Slot(int, int, bool)
    def select(self, dr, c, extend):
        if not self.table:
            return
        n = self.table.n
        self._cur = (max(0, min(n - 1, dr)), max(0, min(n - 1, c)))
        if not extend:
            self._anchor = self._cur
        self._model.refresh([CellModel.SelectedRole])
        self.selectionChanged.emit()

    @Slot(int, int, bool)
    def move(self, ddr, ddc, extend):
        self.select(self._cur[0] + ddr, self._cur[1] + ddc, extend)

    @Slot()
    def selectAll(self):
        if self.table:
            self._anchor, self._cur = (0, 0), (self.table.n - 1, self.table.n - 1)
            self._model.refresh([CellModel.SelectedRole])
            self.selectionChanged.emit()

    def _apply(self, fn):
        """fn(valores_em_eng_snapshot, r, c) -> novo valor em eng para cada celula selecionada."""
        if not self.table:
            return
        t = self.table
        before = [row[:] for row in t.values]
        eng = [[t.eng(v) for v in row] for row in before]
        lo, hi = sorted((t.eng(0), t.eng(255)))
        for r, c in self._selected():
            t.values[r][c] = t.raw(max(lo, min(hi, fn(eng, r, c))))
        if t.values == before:
            return
        self._undo.append(before)
        del self._undo[:-100]
        self._commit()

    def _commit(self):
        self._update_range()
        self._model.refresh()
        self.cellsChanged.emit()
        self.tableChanged.emit()
        self.selectionChanged.emit()
        self.worker.write_table(self.name, self.table.to_bytes())

    @Slot(int)
    def nudge(self, steps):
        self._apply(lambda e, r, c: e[r][c] + steps * self._step())

    @Slot(str, result=bool)
    def setValue(self, text):
        try:
            value = float(text.replace(',', '.'))
        except ValueError:
            return False
        self._apply(lambda e, r, c: value)
        return True

    @Slot(float)
    def scaleBy(self, pct):
        self._apply(lambda e, r, c: e[r][c] * (1 + pct / 100.0))

    @Slot()
    def interpolate(self):
        """Preenche a selecao por interpolacao bilinear a partir dos quatro cantos."""
        cells = self._selected()
        if not cells:
            return
        rows = sorted({r for r, _ in cells})
        cols = sorted({c for _, c in cells})
        r0, r1, c0, c1 = rows[0], rows[-1], cols[0], cols[-1]

        def f(e, r, c):
            u = 0.0 if c1 == c0 else (c - c0) / (c1 - c0)
            w = 0.0 if r1 == r0 else (r - r0) / (r1 - r0)
            top = e[r0][c0] * (1 - u) + e[r0][c1] * u
            bottom = e[r1][c0] * (1 - u) + e[r1][c1] * u
            return top * (1 - w) + bottom * w
        self._apply(f)

    @Slot()
    def smooth(self):
        n = self.table.n if self.table else 0

        def f(e, r, c):
            near = [e[i][j] for i in range(r - 1, r + 2) for j in range(c - 1, c + 2)
                    if 0 <= i < n and 0 <= j < n]
            return sum(near) / len(near)
        self._apply(f)

    @Slot()
    def undo(self):
        if self._undo and self.table:
            self.table.values = self._undo.pop()
            self._commit()

    @Slot()
    def burn(self):
        if self.table:
            self._set_status('gravando na flash...')
            self.worker.burn_page(locate(self.name)[0])

    @Slot()
    def reload(self):
        if self.name:
            self.open(self.name)

    @Slot(QObject)
    def fillSurface(self, series):
        """Superficie 3D: X = RPM, Z = carga, Y = valor. Eixo invalido vira indice, senao a
        malha dobra sobre si mesma."""
        t = self.table
        if not t:
            return
        xs = t.rpm if all(a < b for a, b in zip(t.rpm, t.rpm[1:])) else list(range(t.n))
        zs = t.load if all(a < b for a, b in zip(t.load, t.load[1:])) else list(range(t.n))
        rows = [[QSurfaceDataItem(QVector3D(xs[c], t.eng(t.values[r][c]), zs[r])) for c in range(t.n)]
                for r in range(t.n)]
        series.dataProxy().resetArray(rows)

    # ------------------------------------------------------------ propriedades

    def _sel_info(self):
        if not self.table:
            return ''
        cells = self._selected()
        vals = [self.table.eng(self.table.values[r][c]) for r, c in cells]
        if len(cells) == 1:
            r, c = cells[0]
            return '%s rpm × %s  =  %s %s' % (self.table.rpm[c], self.table.load[r],
                                              self.fmt(vals[0]), self.table.unit)
        return '%d células  ·  mín %s  ·  média %s  ·  máx %s' % (
            len(cells), self.fmt(min(vals)), self.fmt(sum(vals) / len(vals)), self.fmt(max(vals)))

    groups = Property('QVariantList', lambda s: [{'group': g, 'tables': [{'name': n, 'label': l}
                                                                        for n, l in items]}
                                                 for g, items in TABLE_GROUPS], constant=True)
    model = Property(QObject, lambda s: s._model, constant=True)
    currentName = Property(str, lambda s: s.name, notify=tableChanged)
    label = Property(str, lambda s: TABLE_LABELS.get(s.name, s.name), notify=tableChanged)
    size = Property(int, lambda s: s.table.n if s.table else 0, notify=tableChanged)
    unit = Property(str, lambda s: (s.table.unit or 'cru') if s.table else '', notify=tableChanged)
    rpmAxis = Property('QVariantList', lambda s: s.table.rpm if s.table else [], notify=tableChanged)
    loadAxis = Property('QVariantList', lambda s: s.table.load[::-1] if s.table else [], notify=tableChanged)
    status = Property(str, lambda s: s._status, notify=statusChanged)
    dirty = Property(bool, lambda s: bool(s.name) and locate(s.name)[0] in s._dirty, notify=tableChanged)
    canUndo = Property(bool, lambda s: bool(s._undo), notify=tableChanged)
    hasCursor = Property(bool, lambda s: s.name in TABLE_LOAD, notify=tableChanged)
    cursorX = Property(float, lambda s: s._cursor[0], notify=cursorChanged)
    cursorY = Property(float, lambda s: s._cursor[1], notify=cursorChanged)
    selectionInfo = Property(str, _sel_info, notify=selectionChanged)
    valueMin = Property(float, lambda s: s.table.eng(s.range[0]) if s.table else 0, notify=cellsChanged)
    valueMax = Property(float, lambda s: s.table.eng(s.range[1]) if s.table else 1, notify=cellsChanged)


def _raw_bounds(f):
    if f.bits:
        return (-(1 << (f.bits - 1)), (1 << (f.bits - 1)) - 1) if f.signed else (0, (1 << f.bits) - 1)
    span = 1 << (8 * f.elem)
    return (-span // 2, span // 2 - 1) if f.signed else (0, span - 1)


def _eng(spec, raw):
    return raw * spec['scale'] + spec['add']


def _fmt(spec, raw):
    d = spec.get('decimals')
    return '%.*f' % (_decimals(spec['scale']) if d is None else d, _eng(spec, raw))


def _to_raw(spec, f, eng):
    lo, hi = sorted(_eng(spec, r) for r in _raw_bounds(f))
    if spec['lo'] is not None:
        lo = max(lo, spec['lo'])
    if spec['hi'] is not None:
        hi = min(hi, spec['hi'])
    return round((max(lo, min(hi, eng)) - spec['add']) / spec['scale'])


class ConfigEditor(QObject):
    """Paineis de config_panels.PANELS. Cada alteracao vira um patch dos bytes do campo sobre o
    cache de paginas do worker, entao nao pisa em tabela editada na mesma pagina."""
    changed = Signal()
    statusChanged = Signal()

    def __init__(self, worker, live):
        super().__init__()
        self.worker, self.live = worker, live
        self.panel = None
        self._items = []                # (item, pagina, base, Field, 'when' e eixo X como (pagina, base, Field))
        self._pages, self._baseline = {}, {}
        self._pending, self._dirty = set(), set()
        self._reboot = self._kgm = False
        self._status = ''
        worker.pageLoaded.connect(self._on_loaded)
        worker.pageWritten.connect(self._on_written)
        worker.burned.connect(self._on_burned)
        live.linkChanged.connect(self._on_link)

    def _set_status(self, text):
        self._status = text
        self.statusChanged.emit()

    def _get(self, page, base, f):
        return f.get(self._pages[page][base:])

    def _page_set(self):
        return {item[1] for item in self._items} | {loc[0] for item in self._items for loc in item[4:] if loc}

    # ------------------------------------------------------------ ECU -> GUI

    @Slot(int, bytes)
    def _on_loaded(self, page, data):
        if page not in self._page_set():
            return
        self._pages[page] = bytes(data)
        self._baseline.setdefault(page, bytes(data))
        self._pending.discard(page)
        if not self._pending:
            self._set_status('lido da ECU')
            self.changed.emit()

    @Slot(int, bool, str)
    def _on_written(self, page, ok, info):
        if page not in self._page_set():
            return
        if not ok:
            self._set_status('falha na escrita: %s — relendo' % info)
            self._pending.add(page)
            self.worker.load_page(page)
            return
        self._dirty.add(page)
        if self._reboot:
            note = 'vale depois de gravar e reiniciar a ECU'
        elif self._kgm:
            note = 'vale depois de gravar na flash'
        else:
            note = 'não gravado na flash'
        self._set_status('RAM atualizada (%s) — %s' % (info, note))
        self.changed.emit()

    @Slot(int, bool, str)
    def _on_burned(self, page, ok, info):
        if page not in self._dirty:
            return
        if not ok:
            self._set_status('falha no burn: ' + info)
            return
        self._dirty.discard(page)
        if page in self._pages:
            self._baseline[page] = self._pages[page]
        if not self._dirty:
            self._set_status('gravado na flash' + (' — reinicie a ECU para aplicar' if self._reboot else ''))
            self._reboot = self._kgm = False
        self.changed.emit()

    @Slot()
    def _on_link(self):
        if self.live.connected and self.panel:
            self.open(self.panel['id'])

    # ------------------------------------------------------------ GUI -> ECU

    @Slot(str)
    def open(self, panel_id):
        self.panel = next(p for p in PANELS if p['id'] == panel_id)
        self._items = []
        for _title, items in self.panel['groups']:
            for it in items:
                page = base = f = None
                if 'ref' in it:
                    page, base, f = resolve(it['ref'])
                when = resolve(it['when']) if it.get('when') else None
                xloc = resolve(it['xref']) if it.get('xref') else None
                self._items.append((it, page, base, f, when, xloc))
        self._pending = {p for p in self._page_set() if p is not None}
        self._set_status('lendo...')
        self.changed.emit()
        for page in sorted(self._pending):
            self.worker.load_page(page)

    def _write(self, index, raw, loc=None):
        it = self._items[index][0]
        page, base, f = loc or self._items[index][1:4]
        if f is None or it.get('readonly') or page in self._pending or page not in self._pages:
            return
        if raw == self._get(page, base, f):
            return
        sub = bytearray(self._pages[page][base:])
        off, n = f.set(sub, raw)
        data = bytes(sub[off:off + n])
        p = self._pages[page]
        self._pages[page] = p[:base + off] + data + p[base + off + n:]
        self._reboot |= it.get('apply') == 'reboot'
        self._kgm |= it['ref'] in KGM
        self.worker.patch_page(page, base + off, data)
        self.changed.emit()

    @Slot(int, str, result=bool)
    def setText(self, index, text):
        it, _, _, f, _, _ = self._items[index]
        try:
            eng = float(text.replace(',', '.'))
        except ValueError:
            return False
        self._write(index, _to_raw(it, f, eng))
        return True

    @Slot(int, int)
    def nudge(self, index, steps):
        it, page, base, f, _, _ = self._items[index]
        if page in self._pages:
            self._write(index, _to_raw(it, f, _eng(it, self._get(page, base, f) + steps)))

    @Slot(int, int)
    def choose(self, index, raw):
        self._write(index, raw)

    def _cell(self, index, axis, i, eng_fn):
        it, page, base, yf, _, xloc = self._items[index]
        loc, spec = (xloc, it['x']) if axis == 0 else ((page, base, yf), it['y'])
        if loc is None or loc[0] not in self._pages:
            return
        page, base, f = loc
        vals = list(self._get(page, base, f))
        raw = _to_raw(spec, f, eng_fn(_eng(spec, vals[i]), spec))
        if axis == 0:
            # table2D_getValue interpola assumindo eixo crescente.
            if i > 0:
                raw = max(raw, vals[i - 1])
            if i < len(vals) - 1:
                raw = min(raw, vals[i + 1])
        vals[i] = raw
        self._write(index, vals, loc)

    @Slot(int, int, int, str, result=bool)
    def setCell(self, index, axis, i, text):
        try:
            eng = float(text.replace(',', '.'))
        except ValueError:
            return False
        self._cell(index, axis, i, lambda cur, spec: eng)
        return True

    @Slot(int, int, int, int)
    def nudgeCell(self, index, axis, i, steps):
        self._cell(index, axis, i, lambda cur, spec: cur + steps * spec['scale'])

    @Slot()
    def burn(self):
        if self._dirty:
            self._set_status('gravando na flash...')
            for page in sorted(self._dirty):
                self.worker.burn_page(page)

    @Slot()
    def reload(self):
        if self.panel:
            self.open(self.panel['id'])

    # ------------------------------------------------------------ propriedades

    def _series(self, spec, page, base, f):
        vals = self._get(page, base, f)
        old = f.get(self._baseline[page][base:]) if page in self._baseline else vals
        return ([_fmt(spec, v) for v in vals], [_eng(spec, v) for v in vals],
                [a != b for a, b in zip(vals, old)])

    def _row(self, index):
        it, page, base, f, when, xloc = self._items[index]
        curve = it['kind'] == 'curve'
        row = {'index': index, 'kind': it['kind'], 'label': it['label'],
               'detail': it.get('detail', ''), 'note': it.get('note', ''),
               'live': None if curve else it.get('live'), 'cursor': it.get('live') if curve else '',
               'reboot': it.get('apply') == 'reboot', 'readonly': bool(it.get('readonly')),
               'burn': it.get('ref') in KGM and not it.get('readonly'),
               'enabled': True, 'changed': False, 'ready': False}
        if when is not None and when[0] in self._pages:
            row['enabled'] = bool(self._get(*when))
        if f is None or page not in self._pages or xloc and xloc[0] not in self._pages:
            return row
        row['ready'] = True
        if curve:
            row['ys'], row['yv'], row['ychg'] = self._series(it['y'], page, base, f)
            if xloc:
                row['xs'], row['xv'], row['xchg'] = self._series(it['x'], *xloc)
            else:
                n = len(row['ys'])
                row['xs'] = it['xlabels'] or [str(i + 1) for i in range(n)]
                row['xv'], row['xchg'] = list(range(n)), [False] * n
            row['xunit'], row['yunit'] = it['x']['unit'], it['y']['unit']
            row['xedit'] = xloc is not None
            row['changed'] = any(row['xchg']) or any(row['ychg'])
            return row
        raw = self._get(page, base, f)
        row['changed'] = page in self._baseline and raw != f.get(self._baseline[page][base:])
        row['raw'] = raw
        if it['kind'] == 'num':
            row['text'] = _fmt(it, raw)
            row['unit'] = it['unit']
        elif it['kind'] == 'text':
            row['text'] = raw.to_bytes(f.size, 'little').decode('ascii', 'replace')
        else:
            row['options'] = [{'raw': r, 'text': t} for r, t in it['options']]
            row['text'] = next((t for r, t in it['options'] if r == raw), 'cru %d' % raw)
        return row

    def _groups(self):
        if not self.panel:
            return []
        out, i = [], 0
        for title, items in self.panel['groups']:
            out.append({'title': title, 'rows': [self._row(i + k) for k in range(len(items))]})
            i += len(items)
        return out

    panels = Property('QVariantList', lambda s: [{'id': p['id'], 'title': p['title']} for p in PANELS],
                      constant=True)
    current = Property(str, lambda s: s.panel['id'] if s.panel else '', notify=changed)
    title = Property(str, lambda s: s.panel['title'] if s.panel else '', notify=changed)
    groups = Property('QVariantList', _groups, notify=changed)
    status = Property(str, lambda s: s._status, notify=statusChanged)
    dirty = Property(bool, lambda s: bool(s._dirty), notify=changed)
