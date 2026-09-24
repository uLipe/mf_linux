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
KGM = {
    'kgm.acEnrich': (128, 0, 0),    # speeduino_core.cpp:2505, so aplica entre 1 e 50
}


def resolve(ref):
    """-> (pagina, offset do struct na pagina, Field)"""
    if ref in KGM:
        off, bit, bits = KGM[ref]
        return 15, 0, Field('kgm', (ref.split('.')[1], off, bit, bits, 1, False, 1, 'uint8_t'))
    return find_field(ref)


def num(label, ref, scale=1, add=0, unit='', lo=None, hi=None, **kw):
    return dict(kind='num', label=label, ref=ref, scale=scale, add=add, unit=unit, lo=lo, hi=hi, **kw)


def flag(label, ref, on='HABILITADO', off='DESLIGADO', **kw):
    return dict(kind='choice', label=label, ref=ref, options=[(0, off), (1, on)], **kw)


def choice(label, ref, options, **kw):
    return dict(kind='choice', label=label, ref=ref, options=options, **kw)


def info(label, **kw):
    return dict(kind='info', label=label, **kw)


def led(key, bit, color='ok'):
    return {'key': key, 'bit': bit, 'color': color}



AC_ON = 'config15.airConEnable'

PANELS = [
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
]
