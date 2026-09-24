"""Canais ao vivo da ECU KGM, com os rotulos do monitor do MasterFuel 2.9.

Offsets e escalas: speeduino_core/logger.cpp getTSLogEntry(), conferidos contra o codigo
que produz cada campo -- nao contra o speeduino.ini de prateleira.
"""
import struct

# (chave, rotulo no monitor do MasterFuel, byte, tipo, escala, soma, unidade)
# Rotulo None = canal do core sem painel correspondente no monitor do MasterFuel.
CHANNELS = [
    ('secl',          None,                      0,   'U08', 1,     0,   's'),
    ('status1',       None,                      1,   'U08', 1,     0,   'bits'),
    ('engine',        None,                      2,   'U08', 1,     0,   'bits'),
    ('syncLoss',      'SYNC LOSES',              3,   'U08', 1,     0,   ''),
    ('map',           'MAP',                     4,   'U16', 1,     0,   'kPa'),
    ('iat',           'TEMPERATURA AR',          6,   'U08', 1,   -40,   'C'),
    ('clt',           'TEMPERATURA MOTOR',       7,   'U08', 1,   -40,   'C'),
    ('batCorrection', None,                      8,   'U08', 1,     0,   '%'),
    ('battery',       'TENSÃO',                  9,   'U08', 0.1,   0,   'V'),
    ('afr',           'SONDA',                  10,   'U08', 0.1,   0,   'AFR'),
    ('egoCorrection', 'CORREÇÃO DA SONDA',      11,   'U08', 1,     0,   '%'),
    ('iatCorrection', None,                     12,   'U08', 1,     0,   '%'),
    ('wueCorrection', None,                     13,   'U08', 1,     0,   '%'),
    ('rpm',           'RPM',                    14,   'U16', 1,     0,   'rpm'),
    ('accelEnrich',   'ENRIQUECIMENTO',         16,   'U08', 2,     0,   '%'),
    ('gammaE',        None,                     17,   'U16', 1,     0,   '%'),
    ('ve1',           None,                     19,   'U08', 1,     0,   '%'),
    ('ve2',           None,                     20,   'U08', 1,     0,   '%'),
    ('afrTarget',     'ALVO DA SONDA',          21,   'U08', 0.1,   0,   'AFR'),
    ('tpsDot',        None,                     22,   'S16', 1,     0,   ''),
    ('advance',       'IGNIÇÃO',                24,   'S08', 1,     0,   'deg'),
    # sensors.cpp:390 mapeia para 0..200; o comentario em globals.h:489 (0..100) esta errado.
    ('tps',           'TPS',                    25,   'U08', 0.5,   0,   '%'),
    ('loopsPerSec',   None,                     26,   'U16', 1,     0,   'Hz'),
    ('freeRam',       None,                     28,   'U16', 1,     0,   'B'),
    ('boostTarget',   None,                     30,   'U08', 2,     0,   'kPa'),
    ('boostDuty',     None,                     31,   'U08', 1,     0,   '%'),
    ('spark',         None,                     32,   'U08', 1,     0,   'bits'),
    ('rpmDot',        None,                     33,   'S16', 1,     0,   'rpm/s'),
    ('idleLoad',      'IAC PASSO / IAC PWM',    38,   'U08', 1,     0,   ''),
    ('baro',          None,                     41,   'U08', 1,     0,   'kPa'),
    ('tpsAdc',        None,                     74,   'U08', 1,     0,   ''),
    ('pw1',           'TEMPO DE INJEÇÃO',       76,   'U16', 0.001, 0,   'ms'),
    ('status3',       None,                     84,   'U08', 1,     0,   'bits'),
    ('engineProtect', None,                     85,   'U08', 1,     0,   'bits'),
    # Carga usada no lookup das tabelas, no dominio do eixo em memoria (kPa se MAP).
    ('fuelLoad',      None,                     86,   'S16', 1,     0,   ''),
    ('ignLoad',       None,                     88,   'S16', 1,     0,   ''),
    # dwell sai em us: dwellRun (0,1 ms) * 100 em speeduino_core.cpp:1806-1810.
    ('dwell',         'DWELL',                  90,   'U16', 0.001, 0,   'ms'),
    ('idleTarget',    None,                     92,   'U08', 10,    0,   'rpm'),
    ('mapDot',        None,                     93,   'S16', 1,     0,   'kPa/s'),
    ('ve',            'VE',                    102,   'U08', 1,     0,   '%'),
    ('vss',           'VELOCIMETRO',           104,   'U16', 1,     0,   'km/h'),
    ('gear',          None,                    106,   'U08', 1,     0,   ''),
    # Unidade = a de fuelPressureMax/oilPressureMax gravada pelo painel de sensores.
    ('fuelPressure',  'PRESSÃO DO COMBUSTIVEL', 107,  'U08', 1,     0,   'cal'),
    ('oilPressure',   'PRESSÃO DO ÓLEO',       108,   'U08', 1,     0,   'cal'),
    ('status4',       None,                    110,   'U08', 1,     0,   'bits'),
    ('outputsStatus', None,                    115,   'U08', 1,     0,   'bits'),
    ('fanDuty',       'ELETROVENTILADOR',      123,   'U08', 0.5,   0,   '%'),
    ('airConStatus',  'AR CONDICIONADO',       124,   'U08', 1,     0,   'bits'),
    ('actualDwell',   None,                    125,   'U16', 0.001, 0,   'ms'),
]

# Canais do monitor do MasterFuel sem byte proprio no log entry. Provavelmente derivados
# de bits (spark, outputsStatus, airConStatus) ou de PW x RPM; nao mapear por palpite.
UNMAPPED = [
    'DUTY CYCLE', 'CONTROLE LARGADA',
    'ENTRADA PINO 13', 'ENTRADA PINO 14', 'ENTRADA PINO 15', 'ENTRADA PINO 16',
    'ENTRADA PINO 19', 'ENTRADA PINO 20', 'ENTRADA PINO 21', 'ENTRADA PINO 25',
]

_FMT = {'U08': '<B', 'S08': '<b', 'U16': '<H', 'S16': '<h'}


def decode(entry):
    out = {}
    for key, _label, off, typ, scale, add, _unit in CHANNELS:
        raw = struct.unpack_from(_FMT[typ], entry, off)[0]
        out[key] = (raw, raw * scale + add)
    return out


def _fmt_value(val, unit):
    if unit == 'bits':
        return '0x%02X' % int(val)
    if isinstance(val, float) and not val.is_integer():
        return '%.3f' % val if abs(val) < 10 else '%.1f' % val
    return '%d' % val


def render(values, show_all):
    lines = []
    for key, label, off, typ, scale, add, unit in CHANNELS:
        if label is None and not show_all:
            continue
        raw, val = values[key]
        lines.append('%-24s %-14s %10s %-5s  (byte %3d, raw %d)' % (
            label or '', key, _fmt_value(val, unit), unit, off, raw))
    return '\n'.join(lines)
