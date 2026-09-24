"""Protocolo serial da ECU KGM (Speeduino framed, speeduino_core/comms.cpp).

Frame: len 16-bit BE + payload + CRC32 BE. O CRC32 e o refletido padrao com seed
proprietario 0x7A3F9C21 (speeduino_core/src/FastCRC/FastCRCsw.cpp:454), por isso
TunerStudio de prateleira nao conversa com esta ECU.
"""
import struct
import time

import serial

SEED = 0x7A3F9C21

RC_OK = 0x00
RC_BURN_OK = 0x04
RC_NAMES = {
    0x00: 'OK', 0x04: 'BURN_OK', 0x80: 'TIMEOUT', 0x82: 'CRC_ERR', 0x83: 'UNKNOWN_CMD',
    0x84: 'RANGE_ERR', 0x85: 'BUSY', 0xFF: 'NOK',
}

# comms.cpp: kSerialPayloadBytes = serialBufferSize (board_masterfuel_ecu.h:25). Nem a
# recepcao nem o 'p' checam esse limite no firmware -- estourar sobrescreve RAM da ECU.
SERIAL_BUFFER = 517
MAX_READ = SERIAL_BUFFER - 1          # 'p' responde [rc] + dados
MAX_WRITE = SERIAL_BUFFER - 7         # 'M' = 7 bytes de cabecalho + dados
LOG_ENTRY_SIZE = 127
TOOTH_LOG_SIZE = 255

# '#' reinicia no bootloader (comms.cpp:570) e 'U' reseta a placa (comms.cpp:834).
FORBIDDEN = {ord('#'), ord('U')}

STATUS4_BYTE = 110                    # logger.cpp getTSLogEntry
BIT_STATUS4_BURNPENDING = 4           # globals.h:143


def crc(data, init=SEED):
    c = init
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ (0xEDB88320 if c & 1 else 0)
    return (c ^ 0xFFFFFFFF) & 0xFFFFFFFF


class EcuError(IOError):
    def __init__(self, msg, rc=None):
        super().__init__(msg)
        self.rc = rc


class Ecu:
    def __init__(self, port='/dev/ttyUSB0', baud=115200, timeout=2.0, can_id=0):
        self.s = serial.Serial(port, baud, timeout=timeout, rtscts=False, dsrdtr=False)
        # O ftdi_sio segura a recepcao por 16 ms (latency_timer) antes de entregar ao host;
        # em 1 ms o pedido 'r' cai de 28 para 14 ms, que e so o tempo de fio a 115200.
        try:
            self.s.set_low_latency_mode(True)
        except (AttributeError, ValueError, OSError):
            pass
        self.can_id = can_id
        time.sleep(0.2)
        self.s.reset_input_buffer()
        self.blocking_factor, self.table_blocking_factor = self.capabilities()[1:]

    def close(self):
        self.s.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------------------------------------------------------------- framing

    def _read(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.s.read(n - len(buf))
            if not chunk:
                break
            buf += chunk
        return buf

    def transfer(self, payload):
        if not payload:
            raise ValueError('payload vazio')
        if payload[0] in FORBIDDEN:
            raise ValueError('comando %r bloqueado: reinicia a ECU' % chr(payload[0]))
        if len(payload) > SERIAL_BUFFER:
            raise ValueError('payload de %d bytes estoura o buffer da ECU (%d)'
                             % (len(payload), SERIAL_BUFFER))
        self.s.reset_input_buffer()
        self.s.write(struct.pack('>H', len(payload)) + payload + struct.pack('>I', crc(payload)))
        self.s.flush()
        hdr = self._read(2)
        if len(hdr) < 2:
            raise EcuError('sem resposta ao comando %r' % chr(payload[0]))
        n = struct.unpack('>H', hdr)[0]
        body = self._read(n + 4)
        if len(body) < n + 4:
            raise EcuError('resposta truncada: %d de %d bytes' % (len(body), n + 4))
        data = body[:n]
        if struct.unpack('>I', body[n:])[0] != crc(data):
            raise EcuError('CRC invalido na resposta')
        return data

    def _checked(self, payload, ok=(RC_OK,)):
        data = self.transfer(payload)
        if data[0] not in ok:
            raise EcuError('%r devolveu %s' % (chr(payload[0]), RC_NAMES.get(data[0], hex(data[0]))),
                           rc=data[0])
        return data[1:]

    # -------------------------------------------------------------- identidade

    def signature(self):
        return self._checked(b'Q').decode('latin1')

    def product(self):
        return self._checked(b'S').decode('latin1')

    def test_comms(self):
        return self._checked(b'C') == b'\xff'

    def capabilities(self):
        """(versao do protocolo, blocking factor, table blocking factor)."""
        d = self._checked(b'f')
        return d[0], d[1] << 8 | d[2], d[3] << 8 | d[4]

    # --------------------------------------------------------------- ao vivo

    def realtime(self, offset=0, length=LOG_ENTRY_SIZE):
        # generateLiveValues itera com uint8_t: mais de 255 trava a ECU em loop infinito.
        if length > 255 or offset + length > LOG_ENTRY_SIZE:
            raise ValueError('fora do log entry (0..%d, max 255 por pedido)' % LOG_ENTRY_SIZE)
        return self._checked(b'r' + bytes([self.can_id, 0x30])
                             + struct.pack('<HH', offset, length))

    # --------------------------------------------------------------- paginas

    def _page_hdr(self, cmd, page, offset, length):
        return cmd + bytes([self.can_id, page]) + struct.pack('<HH', offset, length)

    def read_page(self, page, size, offset=0, length=None):
        length = size - offset if length is None else length
        if offset < 0 or offset + length > size:
            raise ValueError('fora da pagina %d (%d bytes)' % (page, size))
        step = min(self.blocking_factor, MAX_READ)
        out = bytearray()
        while len(out) < length:
            n = min(step, length - len(out))
            chunk = self._checked(self._page_hdr(b'p', page, offset + len(out), n))
            if len(chunk) != n:
                raise EcuError('pagina %d: pedi %d bytes, vieram %d' % (page, n, len(chunk)))
            out += chunk
        return bytes(out)

    def write_page(self, page, size, offset, data):
        """Escreve na RAM da ECU. Tem efeito imediato no motor; so persiste com burn()."""
        if offset < 0 or offset + len(data) > size:
            raise ValueError('fora da pagina %d (%d bytes)' % (page, size))
        step = min(self.blocking_factor, MAX_WRITE)
        for i in range(0, len(data), step):
            chunk = data[i:i + step]
            self._checked(self._page_hdr(b'M', page, offset + i, len(chunk)) + bytes(chunk))

    def write_changes(self, page, old, new):
        """Escreve so os trechos de `new` que diferem de `old` (pagina inteira) e confere
        o resultado pelo CRC da pagina. Devolve quantos bytes mudaram."""
        if len(old) != len(new):
            raise ValueError('tamanhos diferentes')
        changed, i = 0, 0
        while i < len(new):
            if old[i] == new[i]:
                i += 1
                continue
            j = i
            while j < len(new) and old[j] != new[j]:
                j += 1
            self.write_page(page, len(new), i, new[i:j])
            changed += j - i
            i = j
        got = self.page_crc(page)
        if got != crc(new):
            raise EcuError('pagina %d: CRC da ECU %08X != esperado %08X' % (page, got, crc(new)))
        return changed

    def page_crc(self, page):
        return struct.unpack('>I', self._checked(b'd' + bytes([self.can_id, page])))[0]

    def burn_pending(self):
        return bool(self.realtime(STATUS4_BYTE, 1)[0] & (1 << BIT_STATUS4_BURNPENDING))

    def burn(self, page, timeout=5.0):
        """Grava a pagina na flash. O firmware responde BURN_OK mesmo quando so ADIA a
        gravacao (comms.cpp:584-594); aqui espera o BURNPENDING baixar para confirmar."""
        self._checked(b'b' + bytes([self.can_id, page]), ok=(RC_BURN_OK,))
        t0 = time.monotonic()
        while self.burn_pending():
            if time.monotonic() - t0 > timeout:
                raise EcuError('burn da pagina %d ainda pendente apos %.1f s' % (page, timeout))
            time.sleep(0.1)

    # ------------------------------------------------------------ calibracao

    def calibration_crc(self, table):
        """CRC das tabelas de calibracao ('k'): 0 = O2, 1 = IAT, 2 = CLT."""
        return struct.unpack('>I', self._checked(b'k' + bytes([self.can_id, table])))[0]

    # ---------------------------------------------------------------- loggers

    def tooth_logger(self, on):
        self._checked(b'H' if on else b'h')

    def composite_logger(self, on):
        self._checked(b'J' if on else b'j')

    def read_tooth_log(self):
        """Tooth logger: [us entre dentes]. Composite: [(us acumulado, status)].
        Se o buffer ainda nao encheu, a ECU completa com zeros (comms.cpp sendToothLog)."""
        d = self._checked(b'T')
        if len(d) == TOOTH_LOG_SIZE * 4:
            return list(struct.unpack('>%dI' % TOOTH_LOG_SIZE, d))
        if len(d) == TOOTH_LOG_SIZE * 5:
            return [struct.unpack_from('>IB', d, i * 5) for i in range(TOOTH_LOG_SIZE)]
        raise EcuError('log de dentes com %d bytes' % len(d))

    # ---------------------------------------------------------------- botoes

    def command_button(self, code):
        """Comando de botao do TS (TS_CommandButtonHandler), ex.: testes de saida."""
        self._checked(b'E' + struct.pack('>H', code))
