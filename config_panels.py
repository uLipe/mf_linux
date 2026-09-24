"""Paineis de configuracao com os rotulos e faixas dos forms do MasterFuel 2.9.

Escalas conferidas no codigo que consome cada campo e no speeduino.ini da propria firmware
(ecu_firmware/misc/reference/speeduino.ini, ja com as mudancas [ELST]).

apply='reboot': lido so no init da ECU (requiresPowerCycle no ini).
Campos 'kgm.*' valem so depois do burn: app_kgm_config_set() roda quando a pagina 15 vai para a
flash (storage.cpp:309), nao quando a RAM muda.
"""
from pages import Field, find_field

# Configuracao propria da KGM dentro de configPage15.Unused15_98_255. Offsets absolutos da
# pagina 15, iguais aos comentarios "Byte N" de app_kgm.cpp (config15 comeca no byte 80).
# (offset, bit, bits, bytes, signed), little-endian; bits == 0 -> inteiro de `bytes` bytes.
KGM = {
    'kgm.acEnrich': (128, 0, 0, 1, False),    # speeduino_core.cpp:2505, so aplica entre 1 e 50
    # ignicao
    'kgm.fase':        (111, 3, 1, 1, False),   # init.cpp:1503 (pinTrigger2), lido no init
    'kgm.ignOutVolt':  (111, 1, 1, 1, False),   # app_kgm.cpp:409-420, relé PE12
    'kgm.crankSensor': (111, 2, 1, 1, False),   # app_kgm.cpp:423-426, relé PE11
    # sensores
    # app_kgm.cpp:805-806 -> sensors.cpp:646/700. 0 personalizado, 1 Marflex, 2 0-10 bar, 3 0-100 psi
    'kgm.fuelPressSensor': (130, 0, 4, 1, False),
    'kgm.oilPressSensor':  (130, 4, 4, 1, False),
    # app_kgm.cpp:1108-1116, u16 little-endian em centivolts (sensors.cpp:817 convertVoltageToAdc)
    'kgm.fuelPressVmin': (180, 0, 0, 2, False),
    'kgm.fuelPressVmax': (182, 0, 0, 2, False),
    'kgm.oilPressVmin':  (184, 0, 0, 2, False),
    'kgm.oilPressVmax':  (186, 0, 0, 2, False),
    # partidamotor
    'kgm.startStop': (111, 4, 1, 1, False),   # app_kgm.cpp:1153 -> ConfigAlarm, app_can.cpp:227
    'kgm.startTime': (190, 0, 0, 1, False),   # app_kgm.cpp:1123, 1886-1892
    # marchalenta
    'kgm.idleOLtoCLTime': (123, 0, 0, 2, False),     # idle.cpp:848,858,1133 via app_kgm.cpp:786
    'kgm.idleSolenoidEnrich': (125, 0, 0, 1, False),  # speeduino_core.cpp:2526
    'kgm.idleFanEnable': (112, 2, 1, 1, False),       # app_kgm.h:345, speeduino_core.cpp:2487
    'kgm.idleFanAdder': (126, 0, 0, 1, False),        # idle.cpp:905,1843
    'kgm.idleFanEnrich': (127, 0, 0, 1, False),       # speeduino_core.cpp:2492
    # alarmes
    'kgm.protTempEnable':      (172, 2, 1, 1, False),   # engineProtection.cpp:376
    'kgm.protTempLimit':       (178, 0, 0, 1, False),   # engineProtection.cpp:379, em °C
    'kgm.protFuelPressEnable': (172, 4, 1, 1, False),   # engineProtection.cpp:332
    'kgm.protFuelPressLimit':  (179, 0, 0, 1, False),   # engineProtection.cpp:334-338, em psi
    # avisos
    'kgm.avisoBoostEnable':     (172, 1, 1, 1, False),  # app_kgm.cpp:1143
    'kgm.avisoTempEnable':      (172, 3, 1, 1, False),  # app_kgm.cpp:1144
    'kgm.avisoFuelPressEnable': (172, 5, 1, 1, False),  # app_kgm.cpp:1145
    'kgm.avisoOilEnable':       (172, 7, 1, 1, False),  # app_kgm.cpp:1146
    'kgm.avisoRpmEnable':       (173, 5, 1, 1, False),  # app_kgm.cpp:1151
    'kgm.avisoBoostLimit':      (232, 0, 0, 1, False),  # kPa / 2
    'kgm.avisoTempLimit':       (233, 0, 0, 1, False),  # °C
    'kgm.avisoFuelPressLimit':  (234, 0, 0, 1, False),  # bar x 10
    'kgm.avisoOilLimit':        (235, 0, 0, 1, False),  # bar x 10
    'kgm.avisoRpmLimit':        (238, 0, 0, 1, False),  # rpm / 100
    # senhas
    'kgm.senhaAppEnable':   (112, 0, 1, 1, False),  # app_kgm.cpp:726, consumido em :1540
    'kgm.senhaEstacEnable': (112, 1, 1, 1, False),  # app_kgm.cpp:726, consumido em :1573
    # 4 dígitos ASCII na ordem do texto (byte 113 = 1º dígito). Não é inteiro little-endian.
    'kgm.senhaApp':         (113, 0, 0, 4, False),  # app_kgm.cpp:743-746
    'kgm.senhaEstac':       (117, 0, 0, 4, False),  # app_kgm.cpp:760-763
    'kgm.rpmCorte':         (121, 0, 0, 2, False),  # app_kgm.cpp:772-773, uint16 little-endian
}


def resolve(ref):
    """-> (pagina, offset do struct na pagina, Field)"""
    if ref in KGM:
        off, bit, bits, size, signed = KGM[ref]
        return 15, 0, Field('kgm', (ref.split('.')[1], off, bit, bits, size, signed, 1, 'kgm'))
    return find_field(ref)


def num(label, ref, scale=1, add=0, unit='', lo=None, hi=None, decimals=None, **kw):
    return dict(kind='num', label=label, ref=ref, scale=scale, add=add, unit=unit, lo=lo, hi=hi,
                decimals=decimals, **kw)


def flag(label, ref, on='HABILITADO', off='DESLIGADO', **kw):
    return dict(kind='choice', label=label, ref=ref, options=[(0, off), (1, on)], **kw)


def choice(label, ref, options, **kw):
    return dict(kind='choice', label=label, ref=ref, options=options, **kw)


def info(label, **kw):
    return dict(kind='info', label=label, **kw)


def led(key, bit, color='ok'):
    return {'key': key, 'bit': bit, 'color': color}


def value(key, unit='', decimals=0):
    return {'key': key, 'unit': unit, 'decimals': decimals}


def text(label, ref, **kw):
    """Texto ASCII gravado byte a byte na ordem de leitura (senhas da area KGM); so leitura."""
    return dict(kind='text', label=label, ref=ref, readonly=True, **kw)


def curve(label, x_ref, y_ref, x=(1, 0, ''), y=(1, 0, ''), xlo=None, xhi=None, ylo=None, yhi=None,
          xlabels=None, **kw):
    """Curva 1-D: x_ref e o eixo (crescente), y_ref os valores. x_ref=None: so y, com xlabels.
    x/y = (escala, soma, unidade[, casas decimais])."""
    axis = lambda s, lo, hi: dict(scale=s[0], add=s[1], unit=s[2], lo=lo, hi=hi,
                                  decimals=s[3] if len(s) > 3 else None)
    return dict(kind='curve', label=label, ref=y_ref, xref=x_ref, x=axis(x, xlo, xhi),
                y=axis(y, ylo, yhi), xlabels=xlabels, **kw)


AC_ON = 'config15.airConEnable'
BOOST_ON = 'config6.boostEnabled'

PANELS = [
    {'id': 'motor', 'title': 'Motor', 'groups': [
        ('Cálculo de combustível', [
            num('Combustível base (reqFuel)', 'config2.reqFuel', 0.1, unit='ms', lo=0, hi=25.5,
                apply='reboot',
                detail='tempo por injeção com VE 100 %; calculado a partir de cilindrada, '
                       'vazão, cilindros, injetores e AFR'),
            choice('Número de cilindros', 'config2.nCylinders',
                   [(1, '1'), (2, '2'), (3, '3'), (4, '4'), (6, '6'), (8, '8')], apply='reboot',
                   detail='a placa tem 4 saídas de injetor e 4 de ignição'),
            num('Número de injetores', 'config2.nInjectors', lo=1, hi=8, apply='reboot'),
            num('AFR estequiométrico', 'config2.stoich', 0.1, unit='AFR', lo=5, hi=25,
                detail='etanol 9,0 · gasolina 14,7 · gasolina E30 13,2; 9,0 ativa a correção de '
                       'aceleração a frio do etanol'),
            num('Divisor de injeção', 'config2.divider', lo=1, hi=8, apply='reboot',
                detail='cilindros ÷ injeções por ciclo (ex.: 4 cilindros, 2 injeções = 2)'),
            choice('Tipo de injeção', 'config2.injTiming', [(0, 'Simultânea'), (1, 'Alternada')],
                   apply='reboot'),
            choice('Modo de injeção', 'config2.injLayout',
                   [(0, 'Emparelhado'), (1, 'Semi-sequencial'), (3, 'Sequencial')], apply='reboot'),
        ]),
        ('Características do injetor', [
            num('Capacidade dos injetores', 'config2.dutyLim', unit='%', lo=0, hi=90,
                detail='duty máximo; o pulso é limitado a essa fração do ciclo'),
        ]),
        ('Motor', [
            choice('Tipo de mapa', 'config2.fuelAlgorithm', [(0, 'MAP'), (1, 'TPS')],
                   detail='carga do mapa de combustível (aspirado e turbo usam MAP)'),
            choice('Ciclo do motor', 'config2.strokes', [(0, 'Quatro tempos'), (1, 'Dois tempos')],
                   apply='reboot'),
            choice('Ordem de ignição', 'config4.inj4cylPairing',
                   [(0, '1 - 3 & 4 - 2'), (1, '1 - 4 & 3 - 2')], apply='reboot',
                   detail='pares de injetores no semi-sequencial de 4 cilindros'),
            choice('Tipo de motor', 'config2.engineType',
                   [(0, 'Mesmo ângulo'), (1, 'Ângulo diferente')], apply='reboot'),
            num('Ângulo do cilindro 2', 'config2.oddfire2', unit='°', lo=0, hi=720,
                when='config2.engineType', apply='reboot'),
            num('Ângulo do cilindro 3', 'config2.oddfire3', unit='°', lo=0, hi=720,
                when='config2.engineType', apply='reboot'),
            num('Ângulo do cilindro 4', 'config2.oddfire4', unit='°', lo=0, hi=720,
                when='config2.engineType', apply='reboot'),
        ]),
        ('Tempo de abertura do injetor', [
            choice('Compensação de tensão', 'config2.battVCorMode',
                   [(0, 'Pulso completo'), (1, 'Somente tempo aberto')]),
            num('Tempo morto', 'config2.injOpen', 0.1, unit='ms', lo=0.1, hi=25.5, apply='reboot'),
            curve('Ângulo de fechamento do injetor', 'config2.injAngRPM', 'config2.injAng',
                  x=(100, 0, 'rpm'), y=(1, 0, '°'), xlo=100, xhi=10000, ylo=0, yhi=720,
                  live='rpm'),
        ]),
        ('Estado ao vivo', [
            info('Motor funcionando', live=led('engine', 0)),
            info('Partida', live=led('engine', 1, 'marker')),
        ]),
    ]},
    {'id': 'ignicao', 'title': 'Ignição', 'groups': [
        ('Ignição', [
            choice('Tipo de ignição', 'config4.TrigPattern',
                   [(0, 'Roda fônica'), (1, 'Distribuidor')], apply='reboot'),
            choice('Sinal de rotação', 'config4.TrigSpeed',
                   [(0, 'Virabrequim'), (1, 'Comando de válvulas')], apply='reboot'),
            num('Número de dentes', 'config4.triggerTeeth', unit='dentes', lo=0, hi=255,
                apply='reboot', detail='contando os dentes que faltam (60-2 = 60)'),
            num('Falta de dentes', 'config4.triggerMissingTeeth', unit='dentes', lo=0, hi=255,
                apply='reboot'),
            num('Alinhamento da roda fônica', 'config4.triggerAngle', unit='°', lo=-360, hi=360,
                detail='ângulo do dente 1 em relação ao PMS do cilindro 1'),
            num('Pulso antes da partida', 'config4.StgCycles', unit='voltas', lo=0, hi=255,
                detail='voltas do motor sem injeção e sem ignição no começo da partida'),
            choice('Borda do sinal de rotação', 'config4.TrigEdge',
                   [(0, 'SUBIDA (invertida)'), (1, 'DESCIDA (padrão)')], apply='reboot'),
            choice('Filtro de rotação', 'config4.triggerFilter',
                   [(0, 'Desligado'), (1, 'Baixo'), (2, 'Médio'), (3, 'Alto')]),
            flag('Fase', 'kgm.fase', apply='reboot',
                 detail='habilita a entrada do sensor de fase (comando)'),
            choice('Sinal do sensor de fase', 'config4.trigPatternSec',
                   [(0, 'Uma falha no comando'), (1, 'Quatro falhas no comando'),
                    (2, 'Nível de sondagem'), (3, 'Rover 5-3-2 cam')],
                   when='kgm.fase', apply='reboot'),
            choice('Nível de sondagem', 'config4.PollLevelPolarity', [(0, 'BAIXA'), (1, 'ALTA')],
                   when='kgm.fase', apply='reboot',
                   detail='só no modo "Nível de sondagem"; também define a borda do sinal de fase'),
            choice('Borda do sinal de fase', 'config4.TrigEdgeSec', [(0, 'SUBIDA'), (1, 'DESCIDA')],
                   when='kgm.fase', apply='reboot'),
            choice('Tipo de mapa de ignição', 'config2.ignAlgorithm',
                   [(0, 'MAP'), (1, 'TPS'), (2, 'IMAP/EMAP')]),
            choice('Modo de ignição', 'config4.sparkMode',
                   [(0, 'Centelha perdida - bobina dupla'), (1, 'Bobina única ou distribuidor'),
                    (2, 'Semi-sequencial (cilindros gêmeos) IGN1/IGN3 e IGN2/IGN4'),
                    (3, 'Sequencial')], apply='reboot'),
            choice('Tipo de sinal de ignição', 'config4.IgInv', [(0, 'BAIXO'), (1, 'ALTO')],
                   apply='reboot', detail='BAIXO: a centelha ocorre quando a saída vai a nível baixo'),
        ]),
        ('Configuração do dwell', [
            num('Dwell na partida', 'config4.dwellCrank', 0.1, unit='ms', lo=0, hi=25),
            flag('Usa mapa de dwell', 'config2.useDwellMap', on='SIM', off='NÃO',
                 detail='com SIM, o dwell após a partida vem do mapa de dwell'),
            num('Dwell após a partida', 'config4.dwellRun', 0.1, unit='ms', lo=0, hi=8),
            num('Duração da centelha', 'config4.sparkDur', 0.1, unit='ms', lo=0, hi=25.5),
            flag('Usar proteção de dwell', 'config4.useDwellLim', on='LIGADO'),
            num('Tempo máximo de dwell', 'config4.dwellLimit', unit='ms', lo=0, hi=32,
                when='config4.useDwellLim'),
        ]),
        ('Hardware', [
            choice('Relé da tensão da saída de ignição (5 V / 12 V)', 'kgm.ignOutVolt',
                   [(0, 'DESLIGADO'), (1, 'LIGADO')], readonly=True,
                   detail='o firmware só copia o bit para o relé (PE12); qual nível é 5 V ou 12 V '
                          'depende da placa'),
            choice('Relé do tipo de sensor de rotação (HALL / indutivo)', 'kgm.crankSensor',
                   [(0, 'DESLIGADO'), (1, 'LIGADO')], readonly=True,
                   detail='o firmware só copia o bit para o relé (PE11); qual nível é HALL ou '
                          'indutivo depende da placa'),
        ]),
        ('Eventos de ignição por dente', [
            flag('Habilitar tempo por dente', 'config2.perToothIgn'),
            flag('Correção de erro de dwell', 'config4.dwellErrCorrect',
                 when='config2.perToothIgn'),
        ]),
        ('Estado ao vivo', [
            info('Sincronismo', live=led('spark', 7)),
            info('Meia sincronia (sem fase)', live=led('status3', 4, 'warn')),
            info('Perdas de sincronismo', live=value('syncLoss')),
            info('Avanço', live=value('advance', '°')),
            info('Dwell', live=value('dwell', 'ms', 2)),
            info('Partida', live=led('engine', 1, 'marker')),
            info('Motor funcionando', live=led('engine', 0)),
        ]),
    ]},
    {'id': 'sensores', 'title': 'Sensores e calibração', 'groups': [
        ('Calibrar sensor TPS', [
            num('Tensão do TPS fechado', 'config2.tpsMin', 5 / 255, unit='V', lo=0, hi=5,
                decimals=2, detail='use o valor ao vivo de tpsAdc com a borboleta solta'),
            num('Tensão do TPS aberto', 'config2.tpsMax', 5 / 255, unit='V', lo=0, hi=5,
                decimals=2, detail='use o valor ao vivo de tpsAdc com a borboleta toda aberta'),
        ]),
        ('Sensor de pressão do combustível', [
            flag('Sensor de pressão do combustível', 'config10.fuelPressureEnable', apply='reboot'),
            choice('Sensores comuns', 'kgm.fuelPressSensor',
                   [(0, 'PERSONALIZADO'), (1, 'MARFLEX'), (2, '0–10 BAR (0–5 V)'),
                    (3, '0–100 PSI (0–5 V)')],
                   when='config10.fuelPressureEnable',
                   detail='PERSONALIZADO/MARFLEX: tensão mín. = 0 e tensão máx. = pressão máxima; '
                          'demais: 0–5 V entre pressão mín. e máx.'),
            num('Pressão mínima (tensão)', 'kgm.fuelPressVmin', 0.01, unit='V', lo=0, hi=5,
                when='config10.fuelPressureEnable',
                detail='só PERSONALIZADO/MARFLEX; vale após gravar na ECU'),
            num('Pressão máxima (tensão)', 'kgm.fuelPressVmax', 0.01, unit='V', lo=0, hi=5,
                when='config10.fuelPressureEnable',
                detail='só PERSONALIZADO/MARFLEX; precisa ser maior que a mínima'),
            num('Pressão mínima', 'config10.fuelPressureMin', 0.0689476, unit='bar', decimals=2,
                when='config10.fuelPressureEnable', detail='ignorada em PERSONALIZADO/MARFLEX'),
            num('Pressão máxima', 'config10.fuelPressureMax', 0.0689476, unit='bar', decimals=2,
                when='config10.fuelPressureEnable'),
        ]),
        ('Sensor de pressão do óleo', [
            flag('Sensor de pressão do óleo', 'config10.oilPressureEnable', apply='reboot'),
            choice('Sensores comuns', 'kgm.oilPressSensor',
                   [(0, 'PERSONALIZADO'), (1, 'MARFLEX'), (2, '0–10 BAR (0–5 V)'),
                    (3, '0–100 PSI (0–5 V)')],
                   when='config10.oilPressureEnable',
                   detail='PERSONALIZADO/MARFLEX: tensão mín. = 0 e tensão máx. = pressão máxima; '
                          'demais: 0–5 V entre pressão mín. e máx.'),
            num('Pressão mínima (tensão)', 'kgm.oilPressVmin', 0.01, unit='V', lo=0, hi=5,
                when='config10.oilPressureEnable',
                detail='só PERSONALIZADO/MARFLEX; vale após gravar na ECU'),
            num('Pressão máxima (tensão)', 'kgm.oilPressVmax', 0.01, unit='V', lo=0, hi=5,
                when='config10.oilPressureEnable',
                detail='só PERSONALIZADO/MARFLEX; precisa ser maior que a mínima'),
            num('Pressão mínima', 'config10.oilPressureMin', 0.0689476, unit='bar', decimals=2,
                when='config10.oilPressureEnable', detail='ignorada em PERSONALIZADO/MARFLEX'),
            num('Pressão máxima', 'config10.oilPressureMax', 0.0689476, unit='bar', decimals=2,
                when='config10.oilPressureEnable'),
        ]),
        ('Motor', [
            choice('Método de amostragem MAP', 'config2.mapSample',
                   [(0, 'INSTANTÂNEO'), (1, 'MÉDIA DO CICLO'), (2, 'MÍNIMO DO CICLO'),
                    (3, 'MÉDIA DE EVENTOS')]),
            num('RPM de amostras', 'config2.mapSwitchPoint', 100, unit='rpm', lo=0, hi=16300,
                when='config2.mapSample',
                detail='abaixo deste RPM usa leitura instantânea; 0 desliga'),
        ]),
        ('Calibração da tensão', [
            num('Offset de leitura da tensão', 'config4.batVoltCorrect', 0.1, unit='V', lo=-2, hi=2),
        ]),
        ('Ajuste do ponto de ignição', [
            flag('Travar ponto de ignição', 'config2.fixAngEnable'),
            num('Ponto de ignição fixo', 'config4.FixAng', unit='°', lo=-64, hi=64,
                when='config2.fixAngEnable', detail='na partida vale o ponto de partida'),
        ]),
        ('Configuração do eletroventilador', [
            flag('Eletroventilador', 'config2.fanEnable'),
            flag('Funcionamento com o motor desligado', 'config2.fanWhenOff', on='SIM', off='NÃO',
                 when='config2.fanEnable'),
            flag('Funcionamento na partida', 'config2.fanWhenCranking', on='SIM', off='NÃO',
                 when='config2.fanEnable'),
            num('Liga acima de', 'config6.fanSP', 1, -40, unit='°C', lo=-40, hi=215,
                when='config2.fanEnable'),
            num('Histerese de desligamento', 'config6.fanHyster', unit='°C', lo=0, hi=40,
                when='config2.fanEnable', detail='desliga abaixo de (liga acima de − histerese)'),
        ]),
        ('Bomba de combustível', [
            num('Tempo de ativação', 'config2.fpPrime', unit='s', lo=0, hi=255, apply='reboot',
                detail='escorva ao ligar a ECU; 0 desliga'),
        ]),
        ('Ajuste do tacômetro', [
            choice('Tipo de pulso', 'config6.tachoMode', [(0, 'DURAÇÃO FIXA'), (1, 'DWELL')]),
            choice('Velocidade de saída', 'config2.tachoDiv', [(0, 'NORMAL'), (1, 'METADE DO PULSO')],
                   detail='só em DURAÇÃO FIXA'),
            num('Duração do pulso', 'config2.tachoDuration', unit='ms', lo=1, hi=6,
                detail='só em DURAÇÃO FIXA'),
            flag('Varredura do ponteiro', 'config2.useTachoSweep', apply='reboot'),
            num('RPM máximo do ponteiro', 'config2.tachoSweepMaxRPM', 100, unit='rpm', lo=100,
                hi=10000, when='config2.useTachoSweep', apply='reboot'),
        ]),
        ('Filtros de sensores analógicos', [
            num('Sensor TPS', 'config4.ADCFILTER_TPS', lo=0, hi=240, detail='recomendado 50'),
            num('Sensor de temperatura do motor', 'config4.ADCFILTER_CLT', lo=0, hi=240,
                detail='recomendado 180'),
            num('Sensor de temperatura do ar', 'config4.ADCFILTER_IAT', lo=0, hi=240,
                detail='recomendado 180'),
            num('Sensor lambda', 'config4.ADCFILTER_O2', lo=0, hi=240, detail='recomendado 128'),
            num('Tensão da bateria', 'config4.ADCFILTER_BAT', lo=0, hi=240,
                detail='recomendado 128'),
            num('Sensor MAP', 'config4.ADCFILTER_MAP', lo=0, hi=240,
                detail='recomendado 20; só na amostragem instantânea e dentro do ciclo'),
        ]),
        ('Estado ao vivo', [
            info('Motor em funcionamento', live=led('engine', 0)),
            info('Motor em partida', live=led('engine', 1, 'marker')),
            info('Eletroventilador ligado', live=led('status4', 3, 'accent2')),
        ]),
    ]},
    {'id': 'sonda', 'title': 'Sonda lambda', 'groups': [
        ('Sonda lambda', [
            choice('Tipo de sensor', 'config6.egoType',
                   [(0, 'DESABILITADO'), (1, 'BANDA ESTREITA'), (2, 'BANDA LARGA')],
                   detail='calibre a sonda no painel Sensores e calibração'),
            choice('Algoritmo', 'config6.egoAlgorithm',
                   [(0, 'SIMPLES'), (2, 'PID'), (3, 'NENHUMA CORREÇÃO')], when='config6.egoType'),
        ]),
        ('Correção', [
            num('Quantidade de ciclos para correção', 'config6.egoCount', unit='eventos', lo=1,
                hi=255, when='config6.egoType',
                detail='eventos de ignição entre correções (corrections.cpp:758)'),
            num('Limite de correção +/-', 'config6.egoLimit', unit='%', lo=0, hi=30,
                when='config6.egoType'),
            num('Corrigir acima de', 'config6.ego_min', 0.1, unit='AFR', when='config6.egoType',
                detail='λ = AFR ÷ AFR estequiométrico (painel Motor)'),
            num('Corrigir abaixo de', 'config6.ego_max', 0.1, unit='AFR', when='config6.egoType',
                detail='λ = AFR ÷ AFR estequiométrico (painel Motor)'),
        ]),
        ('Condições de ativação', [
            num('Habilitar acima de', 'config6.egoTemp', 1, -40, unit='°C', lo=-40, hi=102,
                when='config6.egoType'),
            num('Habilitar acima de', 'config6.egoRPM', 100, unit='rpm', lo=100, hi=25500,
                when='config6.egoType'),
            num('Habilitar abaixo do TPS', 'config6.egoTPSMax', 0.5, unit='%', lo=0, hi=100,
                when='config6.egoType'),
            num('Ativo abaixo do MAP', 'config9.egoMAPMax', 2, unit='kPa', lo=2, hi=510,
                when='config6.egoType'),
            num('Ativo acima do MAP', 'config9.egoMAPMin', 2, unit='kPa', lo=2, hi=510,
                when='config6.egoType'),
            num('Atraso para iniciar a sonda', 'config6.ego_sdelay', unit='s', lo=0, hi=120,
                when='config6.egoType', detail='conta desde a partida (runSecs)'),
        ]),
        ('PID', [
            num('Ganho proporcional', 'config6.egoKP', unit='%', lo=0, hi=200, when='config6.egoType',
                detail='só no algoritmo PID'),
            num('Integral', 'config6.egoKI', unit='%', lo=0, hi=200, when='config6.egoType',
                detail='só no algoritmo PID'),
            num('Derivativo', 'config6.egoKD', unit='%', lo=0, hi=200, when='config6.egoType',
                detail='só no algoritmo PID'),
        ]),
        ('Estado ao vivo', [
            info('Motor em funcionamento', live=led('engine', 0)),
            info('Corte em desaceleração (correção congelada)', live=led('status1', 4, 'warn')),
        ]),
    ]},
    {'id': 'partida', 'title': 'Partida do motor', 'groups': [
        ('Botão de partida', [
            flag('Botão de partida', 'kgm.startStop',
                 detail='informa ao painel (IHM) que o botão de partida está habilitado'),
            num('Tempo de partida', 'kgm.startTime', unit='s', lo=0, hi=10, when='kgm.startStop',
                detail='tempo máximo com o motor de arranque acionado; 0 = 10 s'),
        ]),
        ('Configuração de partida', [
            num('RPM de partida', 'config4.crankRPM', 10, unit='rpm', lo=100, hi=1000,
                detail='abaixo dessa rotação o motor é considerado em partida'),
            num('Não injetar acima do TPS', 'config4.floodClear', 0.5, unit='%', lo=0, hi=100,
                detail='corta a injeção durante a partida (desafogar)'),
            num('Prime da bomba de combustível', 'config2.fpPrime', unit='s', lo=0, hi=255,
                apply='reboot', detail='vale na próxima vez que a ECU for ligada'),
            num('Atraso nos injetores', 'config2.primingDelay', 0.1, unit='s', lo=0, hi=25.5,
                apply='reboot', detail='atraso do primeiro pulso após ligar a ECU'),
        ]),
        ('Ignição na partida', [
            num('Ângulo na partida', 'config4.CrankAng', unit='°', lo=-10, hi=80),
        ]),
        ('Primeiro pulso na partida', [
            curve('Primeiro pulso na partida', 'config2.primeBins', 'config2.primePulse',
                  x=(1, -40, '°C'), y=(0.5, 0, 'ms'), xlo=-40, xhi=215, ylo=0, yhi=127.5,
                  live='clt', detail='pulso único ao ligar a ECU; vale na próxima vez que ela ligar'),
        ]),
        ('Enriquecimento na partida', [
            curve('Curva de enriquecimento na partida', 'config10.crankingEnrichBins',
                  'config10.crankingEnrichValues', x=(1, -40, '°C'), y=(5, 0, '%'),
                  xlo=-40, xhi=215, ylo=0, yhi=1275, live='clt'),
        ]),
        ('Estado ao vivo', [
            info('Partida', live=led('engine', 1, 'marker')),
            info('Enriquecimento pós-partida', live=led('engine', 2, 'accent2')),
            info('Motor funcionando', live=led('engine', 0)),
        ]),
    ]},
    {'id': 'marchalenta', 'title': 'Marcha lenta', 'groups': [
        ('Configuração marcha lenta', [
            choice('Tipo de controle de ML', 'config6.iacAlgorithm',
                   [(0, 'Nenhum'), (1, 'Solenóide'), (2, 'PWM malha aberta'),
                    (4, 'Motor de passo malha aberta'), (6, 'PWM MA+MF'), (7, 'Motor de passo MA+MF')],
                   apply='reboot',
                   detail='o firmware reinicializa o controle ao mudar, mas sem homing do motor de passo'),
        ]),
        ('Tempo entre tabelas', [
            num('Tempo após a partida -> malha aberta', 'config2.idleTaperTime', 0.1, unit='s',
                lo=0, hi=25.5, detail='transição da tabela de partida para a de funcionamento'),
            num('Malha aberta -> malha fechada', 'kgm.idleOLtoCLTime', unit='ms', readonly=True,
                detail='valor gravado; a ECU aplica byte 123 + byte 124 (app_kgm.cpp:786), '
                       'que só coincide com ele até 255 ms'),
        ]),
        ('Marcha lenta solenóide', [
            num('Temperatura de fechamento da solenóide', 'config6.iacFastTemp', 1, -40, unit='°C',
                lo=-40, hi=215, detail='solenóide ligada abaixo desta temperatura'),
            num('Enriquecimento de combustível', 'kgm.idleSolenoidEnrich', unit='%', lo=0, hi=50,
                detail='soma à VE com a solenóide ativa e TPS em 0; 0 desliga'),
        ]),
        ('Marcha lenta eletroventilador', [
            flag('Habilitar', 'kgm.idleFanEnable'),
            num('Porcentagem', 'kgm.idleFanAdder', unit='%/passos', lo=0, hi=100,
                when='kgm.idleFanEnable',
                detail='com o ventilador ligado: PWM soma este % do duty (máx. 20 %); '
                       'motor de passo soma este número de passos'),
            num('Enriquecimento de combustível', 'kgm.idleFanEnrich', unit='%', lo=0, hi=50,
                when='kgm.idleFanEnable',
                detail='soma à VE com o ventilador ligado e TPS em 0; 0 desliga'),
        ]),
        ('Marcha lenta malha fechada', [
            num('P', 'config6.idleKP', 0.03125, unit='%', lo=0, hi=7.96),
            num('I', 'config6.idleKI', 0.03125, unit='%', lo=0, hi=7.96),
            num('D', 'config6.idleKD', 0.0078125, unit='%', lo=0, hi=1.99),
            num('Mínimo valor', 'config2.iacCLminValue', unit='%/passos', lo=0, hi=255,
                apply='reboot', detail='PWM: % de duty; motor de passo: valor x3 passos'),
            num('Máximo valor', 'config2.iacCLmaxValue', unit='%/passos', lo=0, hi=255,
                apply='reboot', detail='PWM: % de duty; motor de passo: valor x3 passos'),
            num('Reiniciar integral acima do TPS', 'config2.iacTPSlimit', 0.5, unit='%', lo=0,
                hi=100),
            num('Histerese RPM', 'config2.iacRPMlimitHysteresis', 10, unit='rpm', lo=10, hi=2500,
                detail='zera a integral com RPM acima do alvo mais este valor'),
        ]),
        ('Configuração PWM', [
            num('Frequência PWM', 'config6.idleFreq', 2, unit='Hz', lo=10, hi=510, apply='reboot'),
            choice('Direção PWM', 'config6.iacPWMdir', [(0, 'Normal'), (1, 'Inverter')]),
            flag('Iniciar antes da partida', 'config6.iacPWMrun', on='SIM', off='NÃO'),
        ]),
        ('Configuração motor de passo', [
            num('Tempo de passo', 'config6.iacStepTime', unit='ms', lo=1, hi=6),
            num('Tempo de espera', 'config9.iacCoolTime', unit='ms', lo=0, hi=6),
            num('Passos de início', 'config6.iacStepHome', 3, unit='passos', lo=0, hi=765,
                apply='reboot', detail='homing feito só na partida da ECU'),
            num('Passos mínimos', 'config6.iacStepHyster', unit='passos', lo=1, hi=10),
            num('Não exceder', 'config9.iacMaxSteps', 3, unit='passos', lo=0, hi=765,
                detail='deve ser menor que os passos de início'),
            flag('Inverter passo', 'config9.iacStepperInv', on='SIM', off='NÃO'),
            choice('Motor ligado', 'config9.iacStepperPower', [(0, 'Quando ativado'), (1, 'Sempre')]),
        ]),
        ('Estado ao vivo', [
            info('Controle de marcha lenta ativo', live=led('spark', 6)),
            info('Eletroventilador ligado', live=led('status4', 3, 'accent2')),
        ]),
    ]},
    {'id': 'mapamarchalenta', 'title': 'Mapa de marcha lenta', 'groups': [
        ('Alvo de RPM em marcha lenta', [
            curve('Alvo de RPM', 'config6.iacBins', 'config6.iacCLValues',
                  x=(1, -40, '°C'), y=(10, 0, 'rpm'), xlo=-40, xhi=215, ylo=0, yhi=2550,
                  live='clt', detail='alvo da malha fechada e do avanço por ponto'),
        ]),
        ('Controle de lenta por ponto', [
            curve('Avanço por diferença de RPM', 'config4.idleAdvBins', 'config4.idleAdvValues',
                  x=(10, -500, 'rpm'), y=(1, -15, '°'), xlo=-500, xhi=500, ylo=-15, yhi=50,
                  when='config2.idleAdvEnabled',
                  detail='X = alvo - RPM atual (positivo = abaixo do alvo)'),
            choice('Marcha lenta por ponto', 'config2.idleAdvEnabled',
                   [(0, 'DESLIGADO'), (1, 'ADICIONAR'), (2, 'TABELA')]),
            num('Atraso início do controle de marcha lenta', 'config2.idleAdvDelay', 0.5, unit='s',
                lo=0, hi=15.5, when='config2.idleAdvEnabled', detail='contado a partir do sincronismo'),
            num('Ativo abaixo da rotação', 'config2.idleAdvRPM', 100, unit='rpm', lo=100, hi=25500,
                when='config2.idleAdvEnabled'),
            num('Ativo abaixo do TPS', 'config2.idleAdvTPS', 0.5, unit='%', lo=0, hi=100,
                when='config2.idleAdvEnabled'),
            num('Ativo abaixo da velocidade', 'config2.idleAdvVss', unit='km/h', lo=0, hi=255,
                when='config2.idleAdvEnabled', detail='ignorado sem sensor de velocidade (vssMode 0)'),
            num('Ativo após', 'config9.idleAdvStartDelay', 0.1, unit='s', lo=0, hi=25.5,
                when='config2.idleAdvEnabled', detail='tempo com as condições acima atendidas'),
        ]),
        ('Trabalho IAC PWM na partida', [
            curve('Duty na partida', 'config6.iacCrankBins', 'config6.iacCrankDuty',
                  x=(1, -40, '°C'), y=(1, 0, '%'), xlo=-40, xhi=215, ylo=0, yhi=100, live='clt'),
        ]),
        ('Trabalho IAC PWM', [
            curve('Duty em funcionamento', 'config6.iacBins', 'config6.iacOLPWMVal',
                  x=(1, -40, '°C'), y=(1, 0, '%'), xlo=-40, xhi=215, ylo=0, yhi=100, live='clt',
                  detail='malha aberta e parte fixa do PWM MA+MF'),
        ]),
        ('Motor de passo na partida', [
            curve('Passos na partida', 'config6.iacCrankBins', 'config6.iacCrankSteps',
                  x=(1, -40, '°C'), y=(3, 0, 'passos'), xlo=-40, xhi=215, ylo=0, yhi=765,
                  live='clt'),
        ]),
        ('Motor de passo malha aberta', [
            curve('Passos em funcionamento', 'config6.iacBins', 'config6.iacOLStepVal',
                  x=(1, -40, '°C'), y=(3, 0, 'passos'), xlo=-40, xhi=215, ylo=0, yhi=765,
                  live='clt', detail='malha aberta e parte fixa do motor de passo MA+MF'),
        ]),
        ('Estado ao vivo', [
            info('Controle de marcha lenta ativo', live=led('spark', 6)),
        ]),
    ]},
    {'id': 'injrapida', 'title': 'Injeção rápida', 'groups': [
        ('Curva de injeção rápida', [
            curve('Injeção rápida por TPSdot', 'config4.taeBins', 'config4.taeValues',
                  x=(10, 0, '%/s'), y=(1, 0, '%'), xlo=0, xhi=2550, ylo=0, yhi=255,
                  live='tpsDot', detail='usada com método TPS; soma ao pulso (100 % = sem AE)'),
            curve('Injeção rápida por MAPdot', 'config4.maeBins', 'config4.maeRates',
                  x=(10, 0, 'kPa/s'), y=(1, 0, '%'), xlo=0, xhi=2550, ylo=0, yhi=255,
                  live='mapDot', when='config2.aeMode', detail='usada com método MAP'),
        ]),
        ('Injeção rápida de combustível', [
            choice('Método enriquecimento', 'config2.aeMode', [(0, 'TPS'), (1, 'MAP')]),
            choice('Método de injeção', 'config2.aeApplyMode',
                   [(0, 'MULTIPLICAR PULSO'), (1, 'ADICIONAR PULSO')]),
            num('Limite TPSdot', 'config2.taeThresh', unit='%/s', lo=0, hi=255,
                detail='só no método TPS'),
            num('Mín. variação TPS', 'config2.taeMinChange', 0.5, unit='%', lo=0, hi=5,
                detail='só no método TPS'),
            num('Limite MAPdot', 'config2.maeThresh', unit='kPa/s', lo=0, hi=255,
                when='config2.aeMode'),
            num('Mín. variação MAP', 'config2.maeMinChange', unit='kPa', lo=0, hi=10,
                when='config2.aeMode'),
            num('Tempo de injeção', 'config2.aeTime', 10, unit='ms', lo=0, hi=2550),
            num('Início RPM', 'config2.aeTaperMin', 100, unit='rpm', lo=600, hi=10000,
                detail='acima deste RPM a injeção rápida é reduzida linearmente'),
            num('Final RPM', 'config2.aeTaperMax', 100, unit='rpm', lo=2000, hi=10000,
                detail='acima deste RPM a injeção rápida é zerada'),
        ]),
        ('Configuração injeção rápida', [
            num('Injeção rápida motor frio', 'config2.aeColdPct', unit='%', lo=0, hi=255,
                detail='100 % = sem ajuste'),
            num('Temperatura início injeção rápida', 'config2.aeColdTaperMin', 1, -40, unit='°C',
                lo=-40, hi=215, detail='abaixo dela aplica o ajuste de motor frio inteiro'),
            num('Temperatura final injeção rápida', 'config2.aeColdTaperMax', 1, -40, unit='°C',
                lo=-40, hi=215, detail='acima dela não há ajuste de motor frio'),
        ]),
        ('Empobrecimento desaceleração', [
            num('Quantidade combustível', 'config2.decelAmount', unit='%', lo=0, hi=150,
                detail='multiplica o pulso na desaceleração; 100 % = sem mudança'),
        ]),
        ('Corte de combustível', [
            flag('Habilitar', 'config2.dfcoEnabled'),
            num('Limite abaixo TPS', 'config4.dfcoTPSThresh', 0.5, unit='%', lo=0, hi=100,
                when='config2.dfcoEnabled'),
            num('Temperatura mínima do motor', 'config2.dfcoMinCLT', 1, -40, unit='°C', lo=-40,
                hi=215, when='config2.dfcoEnabled'),
            num('Espera', 'config2.dfcoDelay', 0.1, unit='s', lo=0, hi=25.5,
                when='config2.dfcoEnabled'),
            num('RPM de corte', 'config4.dfcoRPM', 10, unit='rpm', lo=100, hi=2550,
                when='config2.dfcoEnabled'),
            num('RPM histerese', 'config4.dfcoHyster', 2, unit='rpm', lo=100, hi=500,
                when='config2.dfcoEnabled', detail='entra acima de RPM de corte + histerese'),
            flag('Habilitar corte gradual', 'config9.dfcoTaperEnable', when='config2.dfcoEnabled'),
            num('Tempo de corte gradual', 'config9.dfcoTaperTime', 0.1, unit='s', lo=0, hi=25.5,
                when='config9.dfcoTaperEnable'),
            num('Quantidade final de combustível no corte gradual', 'config9.dfcoTaperFuel',
                unit='%', lo=0, hi=255, when='config9.dfcoTaperEnable',
                detail='o combustível vai de 100 % a este valor durante o tempo de corte gradual'),
            num('Retirar avanço gradual', 'config9.dfcoTaperAdvance', unit='°', lo=0, hi=40,
                when='config9.dfcoTaperEnable'),
        ]),
        ('Estado ao vivo', [
            info('Injeção rápida (aceleração)', live=led('engine', 4)),
            info('Empobrecimento (desaceleração)', live=led('engine', 5, 'warn')),
            info('Corte de combustível ativo', live=led('status1', 4, 'warn')),
        ]),
    ]},
    {'id': 'compensacao', 'title': 'Compensações', 'groups': [
        ('Correção temperatura do ar', [
            curve('Quantidade de combustível', 'config6.airDenBins', 'config6.airDenRates',
                  x=(1, -40, '°C'), y=(1, 0, '%'), xlo=-40, xhi=215, ylo=0, yhi=255, live='iat',
                  detail='100 % = sem correção'),
        ]),
        ('Correção de tensão', [
            curve('Dwell', 'config6.voltageCorrectionBins', 'config4.dwellCorrectionValues',
                  x=(0.1, 0, 'V'), y=(1, 0, '%'), xlo=6, xhi=24, ylo=0, yhi=255, live='battery',
                  detail='100 % = sem correção'),
            curve('Injetor', 'config6.voltageCorrectionBins', 'config6.injVoltageCorrectionValues',
                  x=(0.1, 0, 'V'), y=(1, 0, '%'), xlo=6, xhi=24, ylo=0, yhi=255, live='battery',
                  detail='mesmo eixo de tensão do dwell; 100 % = sem correção'),
        ]),
        ('Correção da temperatura do motor', [
            curve('WUE', 'config4.wueBins', 'config2.wueValues',
                  x=(1, -40, '°C'), y=(1, 0, '%'), xlo=-40, xhi=215, ylo=0, yhi=255, live='clt',
                  detail='o último ponto deve ser 100 %; acima dele o WUE fica no último valor'),
        ]),
        ('Correção após partida', [
            curve('Enriquecimento', 'config2.aseBins', 'config2.asePct',
                  x=(1, -40, '°C'), y=(1, 0, '%'), xlo=-40, xhi=215, ylo=0, yhi=155, live='clt',
                  detail='% somado a 100 %'),
            curve('Tempo', 'config2.aseBins', 'config2.aseCount',
                  x=(1, -40, '°C'), y=(1, 0, 's'), xlo=-40, xhi=215, ylo=0, yhi=255, live='clt',
                  detail='mesmo eixo de temperatura do enriquecimento'),
        ]),
        ('Atraso de ignição por temperatura do ar', [
            curve('Atraso', 'config4.iatRetBins', 'config4.iatRetValues',
                  x=(1, 0, '°C'), y=(1, 0, '°'), xlo=0, xhi=125, ylo=0, yhi=30, live='iat',
                  detail='eixo sem o deslocamento de 40 °C'),
        ]),
        ('Avanço de ignição pela temperatura do motor', [
            curve('Avanço', 'config4.cltAdvBins', 'config4.cltAdvValues',
                  x=(1, -40, '°C'), y=(1, -15, '°'), xlo=-40, xhi=215, ylo=-15, yhi=15, live='clt'),
        ]),
        ('Estado ao vivo', [
            info('Aquecimento (WUE)', live=led('engine', 3)),
            info('Após partida (ASE)', live=led('engine', 2)),
            info('Partida', live=led('engine', 1, 'marker')),
        ]),
    ]},
    {'id': 'largada', 'title': 'Controle de largada', 'groups': [
        ('Controle de largada', [
            flag('Habilitar', 'config6.launchEnabled', apply='reboot',
                 detail='o corte usa o tipo de "Corte de proteção" (Alarmes); se estiver DESLIGADO '
                        'a ECU força IGNIÇÃO na RAM durante a largada'),
            num('Mínimo TPS', 'config10.lnchCtrlTPS', 0.5, unit='%', lo=0, hi=100,
                when='config6.launchEnabled'),
            num('Início do controle', 'config6.lnchSoftLim', 100, unit='rpm', lo=100, hi=25500,
                when='config6.launchEnabled'),
            num('Retardo de ignição', 'config6.lnchRetard', 1, unit='°', lo=-30, hi=40,
                when='config6.launchEnabled',
                detail='avanço absoluto aplicado acima do início do controle'),
            num('Limite de rotação', 'config6.lnchHardLim', 100, unit='rpm', lo=100, hi=25500,
                when='config6.launchEnabled'),
            num('Enriquecimento de combustível', 'config6.lnchFuelAdd', 1, unit='%', lo=0, hi=80,
                when='config6.launchEnabled'),
        ]),
        ('Troca rápida (flat shift)', [
            flag('Habilitar flat shift', 'config6.flatSEnable',
                 detail='a entrada da embreagem só é configurada no boot se o controle de largada '
                        'também estiver habilitado'),
            num('Janela do limite suave', 'config6.flatSSoftWin', 100, unit='rpm', lo=100, hi=25500,
                when='config6.flatSEnable'),
            num('Avanço absoluto no limite suave', 'config6.flatSRetard', 1, unit='°', lo=-30, hi=80,
                when='config6.flatSEnable'),
        ]),
        ('Entrada da embreagem', [
            choice('Embreagem acionada com sinal', 'config6.launchHiLo', [(0, 'LOW'), (1, 'HIGH')],
                   apply='reboot'),
            choice('Resistor de pull-up da embreagem', 'config6.lnchPullRes',
                   [(0, 'FLOAT'), (1, 'PULLUP')], apply='reboot'),
            num('RPM de troca largada / flat shift', 'config6.flatSArm', 100, unit='rpm', lo=100,
                hi=25500, detail='embreagem acionada abaixo deste RPM = largada; acima = flat shift'),
        ]),
        ('Troca de marcha', [
            choice('Modo de limite', 'config2.SoftLimitMode', [(0, 'FIXO'), (1, 'RELATIVO AO MAPA')],
                   detail='limite suave só atua com "Corte de proteção" em IGNIÇÃO ou IGNIÇÃO + INJEÇÃO'),
            num('Limite de rotação', 'config4.SoftRevLim', 100, unit='rpm', lo=100, hi=25500),
            num('Grau do limite', 'config4.SoftLimRetard', 1, unit='°', lo=0, hi=80,
                detail='FIXO: avanço absoluto; RELATIVO AO MAPA: retardo sobre o mapa'),
            num('Tempo do limite', 'config4.SoftLimMax', 0.1, unit='s', lo=0, hi=25.5,
                detail='duração máxima do retardo; depois dele o retardo sai e não há corte'),
        ]),
        ('Estado ao vivo', [
            info('Largada: limite de rotação', live=led('spark', 0, 'warn')),
            info('Largada: retardo de ignição', live=led('spark', 1, 'marker')),
            info('Limitador de rotação', live=led('spark', 2, 'warn')),
            info('Limite suave (troca de marcha)', live=led('spark', 3, 'marker')),
        ]),
    ]},
    {'id': 'boost', 'title': 'Controle de boost', 'groups': [
        ('Controle de Boost', [
            flag('Habilitar', BOOST_ON, apply='reboot'),
            choice('Tipo de controle', 'config4.boostType', [(0, 'MALHA ABERTA'), (1, 'MALHA FECHADA')],
                   when=BOOST_ON),
            num('Frequência do solenoide de boost', 'config6.boostFreq', 2, unit='Hz', lo=10, hi=510,
                when=BOOST_ON, apply='reboot'),
            num('Ciclo de trabalho mínimo da válvula', 'config2.boostMinDuty', 1, unit='%', lo=0,
                hi=100, when=BOOST_ON, detail='limite de saída do PID; só em malha fechada'),
            num('Ciclo de trabalho máximo da válvula', 'config2.boostMaxDuty', 1, unit='%', lo=0,
                hi=100, when=BOOST_ON, detail='limite de saída do PID; só em malha fechada'),
        ]),
        ('Configuração de malha fechada', [
            choice('Modo de controle', 'config6.boostMode', [(0, 'SIMPLES'), (1, 'COMPLETO')],
                   when=BOOST_ON, detail='SIMPLES ignora P, I e D (usa 1, 1, 1)'),
            choice('Modo de controle do gatilho', 'config15.boostControlEnable',
                   [(0, 'BAROMÉTRICA'), (1, 'FIXO')], when=BOOST_ON),
            num('Ciclo de trabalho da válvula abaixo do limite', 'config15.boostDCWhenDisabled', 1,
                unit='%', lo=0, hi=100, when=BOOST_ON),
            num('Limite de ativação do controle', 'config15.boostControlEnableThreshold', 1,
                unit='kPa', lo=0, hi=255, when=BOOST_ON, detail='usado com o gatilho FIXO'),
            num('Intervalo de controle', 'config10.boostIntv', 1, unit='ms', lo=0, hi=250,
                when=BOOST_ON),
            num('P', 'config6.boostKP', 1, unit='%', lo=0, hi=200, when=BOOST_ON,
                detail='só no modo COMPLETO'),
            num('I', 'config6.boostKI', 1, unit='%', lo=0, hi=200, when=BOOST_ON,
                detail='só no modo COMPLETO'),
            num('D', 'config6.boostKD', 1, unit='%', lo=0, hi=200, when=BOOST_ON,
                detail='só no modo COMPLETO'),
            num('Sensibilidade', 'config10.boostSens', 1, lo=0, hi=5000, when=BOOST_ON),
        ]),
        ('Corte de Boost', [
            flag('Habilitar', 'config6.boostCutEnabled',
                 detail='mesmo campo da proteção pressão turbo (Alarmes)'),
            num('Limite de pressão', 'config6.boostLimit', 2, unit='kPa', lo=0, hi=510,
                when='config6.boostCutEnabled'),
        ]),
        ('Boost por marcha', [
            choice('Habilitar', 'config9.boostByGearEnabled',
                   [(0, 'DESLIGADO'), (1, '% MULTIPLICADO'), (2, 'LIMITE CONSTANTE')], when=BOOST_ON,
                   detail='exige detecção de marcha pelo VSS (config2.vssMode > 1)'),
        ] + [
            num('Marcha %d' % g, 'config9.boostByGear%d' % g, 2, unit='% / kPa', lo=0, hi=510,
                when='config9.boostByGearEnabled',
                detail='% MULTIPLICADO: % da tabela de boost; LIMITE CONSTANTE: duty % em malha '
                       'aberta, alvo kPa em malha fechada')
            for g in range(1, 7)
        ]),
        ('Estado ao vivo', [
            info('Corte por pressão turbo', live=led('engineProtect', 1, 'warn')),
        ]),
    ]},
    {'id': 'arcond', 'title': 'Ar-condicionado', 'groups': [
        ('Ar-condicionado', [
            flag('Habilita ar-condicionado', AC_ON, apply='reboot'),
            flag('Entrada A/C (pedido)', 'config15.airConReqPol', on='SINAL 12V', off='TERRA',
                 when=AC_ON, apply='reboot'),
            num('Atraso de entrada A/C', 'config15.airConCompOnDelay', 0.1, unit='s', when=AC_ON),
            num('Atraso de entrada A/C após a partida', 'config15.airConAfterStartDelay', 0.1,
                unit='s', when=AC_ON),
        ]),
        ('Limite RPM', [
            num('Mín. RPM para A/C', 'config15.airConMinRPMdiv10', 10, unit='rpm', when=AC_ON),
            num('Máx. RPM para A/C', 'config15.airConMaxRPMdiv100', 100, unit='rpm', when=AC_ON),
            num('Tempo de bloqueio após RPM alto/baixo', 'config15.airConRPMCutTime', 0.1,
                unit='s', when=AC_ON),
        ]),
        ('Limite TPS', [
            num('Desligar A/C acima do TPS', 'config15.airConTPSCut', 0.5, unit='%', hi=100,
                when=AC_ON, detail='religa abaixo desse valor menos 5 %'),
            num('Tempo de bloqueio após TPS alto', 'config15.airConTPSCutTime', 0.1, unit='s',
                when=AC_ON),
        ]),
        ('Temperatura limite', [
            num('Temp. máx. do motor para A/C', 'config15.airConClTempCut', 1, -40, unit='°C',
                when=AC_ON),
        ]),
        ('Marcha lenta para A/C', [
            num('Abertura', 'config15.airConIdleSteps', unit='%/passos', when=AC_ON),
            num('Alvo para marcha lenta', 'config15.airConIdleUpRPMAdder', 10, unit='+rpm', hi=250,
                when=AC_ON),
            num('Enriquecimento de combustível', 'kgm.acEnrich', unit='%', hi=50, when=AC_ON,
                detail='soma à VE com pedido de A/C e TPS em 0; 0 desliga'),
            flag('Ligar ventilador com A/C', 'config15.airConTurnsFanOn', on='SIM', off='NÃO',
                 when=AC_ON),
        ]),
        ('Estado ao vivo', [
            info('Pedido de A/C', live=led('airConStatus', 0)),
            info('Compressor ligado', live=led('airConStatus', 1)),
            info('Aguardando atraso de entrada', live=led('airConStatus', 4, 'marker')),
            info('Bloqueio por RPM', live=led('airConStatus', 2, 'warn')),
            info('Bloqueio por TPS', live=led('airConStatus', 3, 'warn')),
            info('Bloqueio por temperatura', live=led('airConStatus', 5, 'warn')),
            info('Ventilador do A/C', live=led('airConStatus', 6, 'accent2')),
        ]),
    ]},
    {'id': 'alarmes', 'title': 'Alarmes', 'groups': [
        ('Configuração', [
            choice('Corte de proteção', 'config6.engineProtectType',
                   [(0, 'DESLIGADO'), (1, 'IGNIÇÃO'), (2, 'INJEÇÃO'), (3, 'IGNIÇÃO + INJEÇÃO')],
                   detail='DESLIGADO desativa todas as proteções e o limite de rotação; o corte só '
                          'atua acima de config4.engineProtectMaxRPM'),
        ]),
        ('Proteção pressão turbo', [
            flag('Proteção pressão turbo', 'config6.boostCutEnabled'),
            num('Limite de pressão', 'config6.boostLimit', 2, unit='kPa', lo=0, hi=510,
                when='config6.boostCutEnabled', detail='corta com MAP acima do limite'),
        ]),
        ('Proteção temperatura alta do motor', [
            flag('Proteção temperatura alta do motor', 'kgm.protTempEnable'),
            num('Limite de temperatura', 'kgm.protTempLimit', 1, unit='°C', lo=70, hi=150,
                when='kgm.protTempEnable', detail='corta com a temperatura do motor acima do limite'),
        ]),
        ('Proteção pressão baixa de combustível', [
            flag('Proteção pressão baixa de combustível', 'kgm.protFuelPressEnable',
                 detail='exige o sensor de pressão de combustível ligado: sem ele a pressão lida é 0 '
                        'e o corte atua sempre com o motor funcionando'),
            num('Limite de pressão', 'kgm.protFuelPressLimit', 0.0689476, unit='bar', lo=2, hi=6,
                decimals=2, when='kgm.protFuelPressEnable', detail='gravado em psi'),
        ]),
        ('Proteção de pressão do óleo', [
            flag('Proteção de pressão do óleo', 'config10.oilPressureProtEnbl',
                 detail='só atua com o sensor de pressão do óleo ligado (painel de sensores)'),
            num('Atraso no corte da pressão do óleo', 'config10.oilPressureProtTime', 0.1, unit='s',
                lo=0, hi=25, when='config10.oilPressureProtEnbl'),
            curve('Pressão mínima do óleo por RPM', 'config10.oilPressureProtRPM',
                  'config10.oilPressureProtMins', x=(100, 0, 'rpm'), y=(0.0689476, 0, 'bar', 2),
                  xlo=100, xhi=25500, ylo=0, yhi=17.5, live='rpm', when='config10.oilPressureProtEnbl',
                  detail='comparado com a pressão do óleo no valor cru do sensor (psi)'),
        ]),
        ('Proteção de Lambda', [
            choice('Proteção Lambda', 'config9.afrProtectEnabled',
                   [(0, 'DESLIGADO'), (1, 'FIXO'), (2, 'RELATIVO AO MAPA')],
                   detail='exige sonda wideband (config6.egoType)'),
            num('Pressão mínima no coletor', 'config9.afrProtectMinMAP', 2, unit='kPa', lo=0, hi=510,
                when='config9.afrProtectEnabled'),
            num('RPM mínimo do motor', 'config9.afrProtectMinRPM', 100, unit='rpm', lo=100, hi=25500,
                when='config9.afrProtectEnabled'),
            num('Posição mínima do acelerador', 'config9.afrProtectMinTPS', 0.5, unit='%', lo=0, hi=100,
                when='config9.afrProtectEnabled'),
            num('Lambda máximo', 'config9.afrProtectDeviation', 0.1, unit='AFR', lo=0, hi=25.5,
                when='config9.afrProtectEnabled',
                detail='FIXO: AFR máximo; RELATIVO AO MAPA: desvio acima do alvo. '
                       'Lambda = AFR / estequiométrico'),
            num('Atraso no corte', 'config9.afrProtectCutTime', 0.1, unit='s', lo=0, hi=2.5,
                when='config9.afrProtectEnabled'),
            num('Reativar abaixo do acelerador', 'config9.afrProtectReactivationTPS', 0.5, unit='%',
                lo=0, hi=100, when='config9.afrProtectEnabled'),
        ]),
        ('Limite de rotação', [
            choice('Método de corte', 'config9.hardRevMode',
                   [(0, 'DESLIGADO'), (1, 'FIXO'), (2, 'BASEADO NA TEMPERATURA')]),
            num('Rotação de corte', 'config4.HardRevLim', 100, unit='rpm', lo=100, hi=25500,
                when='config9.hardRevMode', detail='usado no método FIXO'),
            curve('Limite de rotação por temperatura', 'config9.coolantProtTemp',
                  'config9.coolantProtRPM', x=(1, -40, '°C'), y=(100, 0, 'rpm'),
                  xlo=-40, xhi=215, ylo=0, yhi=25500, live='clt', when='config9.hardRevMode',
                  detail='usado no método BASEADO NA TEMPERATURA'),
        ]),
        ('Estado ao vivo', [
            info('Corte por rotação', live=led('engineProtect', 0, 'warn')),
            info('Corte por pressão turbo', live=led('engineProtect', 1, 'warn')),
            info('Corte por pressão do óleo', live=led('engineProtect', 2, 'warn')),
            info('Corte por lambda', live=led('engineProtect', 3, 'warn')),
            info('Limite de rotação por temperatura', live=led('engineProtect', 4, 'warn')),
            info('Corte por pressão baixa de combustível', live=led('engineProtect', 5, 'warn')),
            info('Corte por temperatura alta do motor', live=led('engineProtect', 6, 'warn')),
            info('Limitador de rotação', live=led('spark', 2, 'warn')),
        ]),
    ]},
    {'id': 'avisos', 'title': 'Avisos', 'groups': [
        ('Aviso proteção pressão turbo', [
            flag('Aviso de pressão turbo', 'kgm.avisoBoostEnable',
                 detail='aviso só no display (IHM) (IHM via CAN), não corta o motor'),
            num('Limite de pressão', 'kgm.avisoBoostLimit', 2, unit='kPa', lo=100, hi=350,
                when='kgm.avisoBoostEnable'),
        ]),
        ('Aviso proteção temperatura alta do motor', [
            flag('Aviso de temperatura alta do motor', 'kgm.avisoTempEnable',
                 detail='aviso só no display (IHM); só avisa a partir de 70 °C'),
            num('Limite de temperatura', 'kgm.avisoTempLimit', 1, unit='°C', lo=70, hi=150,
                when='kgm.avisoTempEnable'),
        ]),
        ('Aviso proteção pressão baixa de combustível', [
            flag('Aviso de pressão baixa de combustível', 'kgm.avisoFuelPressEnable',
                 detail='aviso só no display (IHM); com o sensor desligado a pressão lida é 0 e o '
                        'aviso dispara com o motor funcionando'),
            num('Limite de pressão', 'kgm.avisoFuelPressLimit', 0.1, unit='bar', lo=1, hi=5,
                when='kgm.avisoFuelPressEnable'),
        ]),
        ('Aviso proteção de pressão do óleo baixa', [
            flag('Aviso de pressão do óleo baixa', 'kgm.avisoOilEnable',
                 detail='aviso só no display (IHM); com o sensor desligado a pressão lida é 0 e o '
                        'aviso dispara com o motor funcionando'),
            num('Limite de pressão', 'kgm.avisoOilLimit', 0.1, unit='bar', lo=0, hi=10,
                when='kgm.avisoOilEnable'),
        ]),
        ('Limite de rotação', [
            flag('Aviso de limite de rotação', 'kgm.avisoRpmEnable', apply='reboot',
                 detail='aviso só no display (IHM); ligar só vale depois de reiniciar a ECU'),
            num('Rotação de corte', 'kgm.avisoRpmLimit', 100, unit='rpm', lo=2000, hi=7000,
                when='kgm.avisoRpmEnable'),
        ]),
    ]},
    {'id': 'senhas', 'title': 'Senhas', 'groups': [
        ('Senha de partida do motor', [
            flag('Senha do aplicativo', 'kgm.senhaAppEnable', readonly=True,
                 detail='imobilizador: com a senha ligada a injeção fica zerada até o display (IHM) '
                        'confirmar a senha via CAN. Sem display (IHM) o motor não pega'),
            text('Senha', 'kgm.senhaApp', when='kgm.senhaAppEnable',
                 detail='4 dígitos, digitados no teclado do display'),
        ]),
        ('Senha de estacionamento', [
            flag('Senha de estacionamento', 'kgm.senhaEstacEnable', readonly=True,
                 detail='modo manobrista: com o modo ativado no display (IHM) a rotação fica limitada '
                        'ao RPM de corte'),
            text('Senha', 'kgm.senhaEstac', when='kgm.senhaEstacEnable',
                 detail='4 dígitos, digitados no teclado do display'),
            num('RPM de corte', 'kgm.rpmCorte', 1, unit='rpm', lo=1000, hi=25500,
                when='kgm.senhaEstacEnable', readonly=True,
                detail='acima de 25500 o limite estoura (rpm/100 em 8 bits)'),
        ]),
        ('Estado ao vivo', [
            info('Corte por rotação (estacionamento ou limitador)', live=led('engineProtect', 0, 'warn')),
        ]),
    ]},
]
