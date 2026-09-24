"""Ponte entre a ECU e o QML.

Uma unica thread e dona da serial: atende a fila de escritas/burns entre um quadro ao vivo
e o proximo. A interface nunca espera a serial -- edicoes entram no cache na hora e a
thread confere cada escrita pelo CRC da pagina; se divergir, a pagina volta ao que a ECU
realmente tem.
"""
import queue
import time

from PySide6.QtCore import (Property, QAbstractTableModel, QModelIndex, QObject, QThread, Qt,
                            Signal, Slot)

from channels import decode
from pages import PAGE_SIZES, PAGES, TABLES, Table, find_field, locate
from protocol import Ecu, EcuError, crc

LIVE_HZ = 60

TABLE_TITLES = {
    've': 'VE', 'ign': 'Avanço de ignição', 'afr': 'Alvo de AFR', 've2': 'VE 2',
    'ign2': 'Avanço de ignição 2', 'dwell': 'Dwell', 'boost': 'Boost', 'boostLookup': 'Duty do boost',
    'vvt': 'VVT', 'vvt2': 'VVT 2', 'staging': 'Staging', 'wmi': 'WMI',
    **{'trim%d' % i: 'Trim cilindro %d' % i for i in range(1, 9)},
}

# Algoritmo que define a carga do eixo Y (speeduino_core.cpp:2450-2580). 0 = MAP, 1 = TPS.
TABLE_LOAD_FIELD = {
    've': 'config2.fuelAlgorithm', 'afr': 'config2.fuelAlgorithm', 'ign': 'config2.ignAlgorithm',
    've2': 'config10.fuel2Algorithm', 'ign2': 'config10.spark2Algorithm',
    'dwell': 'config2.ignAlgorithm',
}


class EcuThread(QThread):
    # object: dict com chave int nao converte para QVariantMap.
    connected = Signal(str, object)
    disconnected = Signal(str)
    live = Signal(object, float)
    pageData = Signal(int, bytes)
    failed = Signal(str)
    burned = Signal(int)

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.jobs = queue.Queue()
        self._stop = False

    def stop(self):
        self._stop = True
        self.wait(3000)

    def run(self):
        while not self._stop:
            try:
                with Ecu(self.port) as ecu:
                    pages = {p: ecu.read_page(p, PAGE_SIZES[p]) for p in PAGES}
                    self.connected.emit(ecu.signature(), pages)
                    self._serve(ecu)
            except (OSError, EcuError, ValueError) as ex:
                self.disconnected.emit(str(ex))
                for _ in range(10):
                    if self._stop:
                        break
                    time.sleep(0.1)

    def _serve(self, ecu):
        period = 1.0 / LIVE_HZ
        frames, t_rate, hz = 0, time.perf_counter(), 0.0
        while not self._stop:
            while True:
                try:
                    job = self.jobs.get_nowait()
                except queue.Empty:
                    break
                self._run(ecu, job)
            t0 = time.perf_counter()
            values = {k: v[1] for k, v in decode(ecu.realtime()).items()}
            frames += 1
            if t0 - t_rate >= 1.0:
                hz, frames, t_rate = frames / (t0 - t_rate), 0, t0
            self.live.emit(values, hz)
            rest = period - (time.perf_counter() - t0)
            if rest > 0:
                time.sleep(rest)

    def _run(self, ecu, job):
        kind, page = job[0], job[1]
        try:
            if kind == 'write':
                offset, data, expected = job[2:]
                ecu.write_page(page, PAGE_SIZES[page], offset, data)
                if ecu.page_crc(page) != crc(expected):
                    raise EcuError('pagina %d: CRC da ECU nao confere apos a escrita' % page)
            elif kind == 'burn':
                ecu.burn(page)
                self.burned.emit(page)
        except EcuError as ex:
            self.failed.emit(str(ex))
            self.pageData.emit(page, ecu.read_page(page, PAGE_SIZES[page]))


def _frac_index(axis, v):
    if v <= axis[0]:
        return 0.0
    for i in range(1, len(axis)):
        if v <= axis[i]:
            span = axis[i] - axis[i - 1]
            return i - 1 + ((v - axis[i - 1]) / span if span > 0 else 0.0)
    return float(len(axis) - 1)


class TableModel(QAbstractTableModel):
    """Linha 0 da view = maior carga, como no TunerStudio; Table guarda linha 0 = menor."""
    TextRole = Qt.UserRole + 1
    NormRole = Qt.UserRole + 2
    RpmRole = Qt.UserRole + 3
    LoadRole = Qt.UserRole + 4

    changed = Signal()
    cursorChanged = Signal()

    def __init__(self, backend, name):
        # Com pai, o QML nao assume a posse e nao coleta o modelo devolvido por table().
        super().__init__(backend)
        self._backend = backend
        self.name = name
        self.page, self.offset, self.size = locate(name)
        self.table = None
        self._lo = self._hi = 0
        self._cx = self._cy = -1.0

    def load(self, page_bytes):
        self.beginResetModel()
        self.table = Table(self.name, page_bytes[self.offset:self.offset + self.size])
        flat = [v for row in self.table.values for v in row]
        self._lo, self._hi = min(flat), max(flat)
        self.endResetModel()
        self.changed.emit()

    def _raw(self, row, col):
        return self.table.values[self.table.n - 1 - row][col]

    def rowCount(self, parent=QModelIndex()):
        return self.table.n if self.table else 0

    def columnCount(self, parent=QModelIndex()):
        return self.table.n if self.table else 0

    def data(self, index, role=Qt.DisplayRole):
        if not self.table or not index.isValid():
            return None
        raw = self._raw(index.row(), index.column())
        if role == Qt.DisplayRole:
            return float(self.table.eng(raw))
        if role == self.TextRole:
            v = self.table.eng(raw)
            return ('%.1f' % v) if isinstance(v, float) and not v.is_integer() else '%d' % v
        if role == self.NormRole:
            return (raw - self._lo) / (self._hi - self._lo) if self._hi > self._lo else 0.5
        if role == self.RpmRole:
            return self.table.rpm[index.column()]
        if role == self.LoadRole:
            return self.table.load[self.table.n - 1 - index.row()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if not self.table or role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self.table.rpm[section])
        return str(self.table.load[self.table.n - 1 - section])

    def roleNames(self):
        return {Qt.DisplayRole: b'display', self.TextRole: b'text', self.NormRole: b'norm',
                self.RpmRole: b'rpm', self.LoadRole: b'load'}

    def update_cursor(self, rpm, load):
        if not self.table:
            return
        cx = _frac_index(self.table.rpm, rpm)
        cy = self.table.n - 1 - _frac_index(self.table.load, load)
        if abs(cx - self._cx) > 1e-3 or abs(cy - self._cy) > 1e-3:
            self._cx, self._cy = cx, cy
            self.cursorChanged.emit()

    title = Property(str, lambda s: TABLE_TITLES.get(s.name, s.name), notify=changed)
    unit = Property(str, lambda s: s.table.unit if s.table else '', notify=changed)
    n = Property(int, lambda s: s.table.n if s.table else 0, notify=changed)
    rpmAxis = Property('QVariantList', lambda s: s.table.rpm if s.table else [], notify=changed)
    loadAxis = Property('QVariantList', lambda s: list(reversed(s.table.load)) if s.table else [],
                        notify=changed)
    warnings = Property('QVariantList', lambda s: s.table.axis_issues() if s.table else [],
                        notify=changed)
    minValue = Property(float, lambda s: float(s.table.eng(s._lo)) if s.table else 0, notify=changed)
    maxValue = Property(float, lambda s: float(s.table.eng(s._hi)) if s.table else 0, notify=changed)
    cursorX = Property(float, lambda s: s._cx, notify=cursorChanged)
    cursorY = Property(float, lambda s: s._cy, notify=cursorChanged)

    @Slot('QVariantList', int)
    def adjust(self, cells, steps):
        """Soma steps (em unidades cruas) as celulas [[linha, coluna], ...]."""
        edits = [(int(r), int(c), max(0, min(255, self._raw(int(r), int(c)) + steps)))
                 for r, c in cells]
        self._apply(edits)

    @Slot('QVariantList', float)
    def setValue(self, cells, value):
        try:
            raw = self.table.raw(value)
        except ValueError as ex:
            self._backend.report(str(ex))
            return
        self._apply([(int(r), int(c), raw) for r, c in cells])

    def _apply(self, edits):
        n = self.table.n
        for r, c, raw in edits:
            self.table.values[n - 1 - r][c] = raw
        self._backend.write_entity(self.page, self.offset, self.table.to_bytes())


class Backend(QObject):
    stateChanged = Signal()
    liveChanged = Signal()
    errorOccurred = Signal(str)
    rendererReady = Signal(str)

    def __init__(self, port):
        super().__init__()
        self._connected = False
        self._status = 'conectando em %s...' % port
        self._signature = ''
        self._live = {}
        self._hz = 0.0
        self._renderer = ''
        self._pages = {}
        self._unburned = set()
        self._models = {}
        self._thread = EcuThread(port)
        self._thread.connected.connect(self._on_connected)
        self._thread.disconnected.connect(self._on_disconnected)
        self._thread.live.connect(self._on_live)
        self._thread.pageData.connect(self._on_page)
        self._thread.failed.connect(self.report)
        self._thread.burned.connect(self._on_burned)
        self.rendererReady.connect(self._set_renderer)
        self._thread.start()

    def shutdown(self):
        self._thread.stop()

    # ------------------------------------------------------------ da thread

    def _on_connected(self, signature, pages):
        self._pages = {p: bytearray(b) for p, b in pages.items()}
        self._unburned.clear()
        self._connected, self._signature, self._status = True, signature, 'conectado'
        for m in self._models.values():
            m.load(self._pages[m.page])
        self.stateChanged.emit()

    def _on_disconnected(self, reason):
        self._connected, self._status = False, 'sem ECU: %s' % reason
        self.stateChanged.emit()

    def _on_live(self, values, hz):
        self._live, self._hz = values, hz
        for name, m in self._models.items():
            m.update_cursor(values['rpm'], self._load_for(name, values))
        self.liveChanged.emit()

    def _on_page(self, page, data):
        self._pages[page] = bytearray(data)
        for m in self._models.values():
            if m.page == page:
                m.load(self._pages[page])

    def _on_burned(self, page):
        self._unburned.discard(page)
        self.stateChanged.emit()

    # -------------------------------------------------------------- escrita

    @Slot(str)
    def report(self, msg):
        self.errorOccurred.emit(msg)

    def write_entity(self, page, offset, data):
        old = self._pages[page]
        new = bytearray(old)
        new[offset:offset + len(data)] = data
        diff = [i for i in range(len(new)) if new[i] != old[i]]
        if not diff:
            return
        lo, hi = diff[0], diff[-1] + 1
        self._pages[page] = new
        self._unburned.add(page)
        self._thread.jobs.put(('write', page, lo, bytes(new[lo:hi]), bytes(new)))
        for m in self._models.values():
            if m.page == page:
                m.load(new)
        self.stateChanged.emit()

    @Slot()
    def burn(self):
        for page in sorted(self._unburned):
            self._thread.jobs.put(('burn', page))

    # --------------------------------------------------------------- consulta

    def _field(self, qualified):
        page, off, f = find_field(qualified)
        return f.get(self._pages[page][off:])

    def _load_for(self, name, values):
        field = TABLE_LOAD_FIELD.get(name)
        if field and self._pages and self._field(field) == 1:
            return values['tps'] * 4
        return values['map']

    @Slot(str, result=QObject)
    def table(self, name):
        if name not in self._models:
            m = TableModel(self, name)
            if self._pages:
                m.load(self._pages[m.page])
            self._models[name] = m
        return self._models[name]

    def _set_renderer(self, text):
        self._renderer = text
        self.stateChanged.emit()

    connected = Property(bool, lambda s: s._connected, notify=stateChanged)
    status = Property(str, lambda s: s._status, notify=stateChanged)
    signature = Property(str, lambda s: s._signature, notify=stateChanged)
    renderer = Property(str, lambda s: s._renderer, notify=stateChanged)
    unburned = Property(int, lambda s: len(s._unburned), notify=stateChanged)
    tableNames = Property('QVariantList', lambda s: [{'name': n, 'title': TABLE_TITLES[n]}
                                                     for n in TABLES], constant=True)
    live = Property('QVariantMap', lambda s: s._live, notify=liveChanged)
    liveHz = Property(float, lambda s: s._hz, notify=liveChanged)
