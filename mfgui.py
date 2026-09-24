#!/usr/bin/env python3
"""Painel grafico da ECU KGM (Qt Quick, renderizado na GPU)."""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def select_gpu(gpu, api):
    """Precisa rodar antes de qualquer import do Qt: o libGL/Vulkan le estas variaveis
    quando carrega, e o Qt Quick escolhe o backend RHI na criacao da primeira janela."""
    if gpu == 'auto':
        gpu = 'nvidia' if os.path.exists('/proc/driver/nvidia') else 'default'
    if gpu == 'nvidia':
        # Optimus: sem isso o Qt Quick renderiza na Intel integrada.
        os.environ['__NV_PRIME_RENDER_OFFLOAD'] = '1'
        os.environ['__GLX_VENDOR_LIBRARY_NAME'] = 'nvidia'
        os.environ['__VK_LAYER_NV_optimus'] = 'NVIDIA_only'
    os.environ['QSG_RHI_BACKEND'] = api


def build_shaders():
    qsb = os.path.join(os.path.dirname(sys.executable), 'pyside6-qsb')
    qsb = qsb if os.path.exists(qsb) else 'pyside6-qsb'
    sdir = os.path.join(HERE, 'shaders')
    for name in os.listdir(sdir):
        if not name.endswith(('.frag', '.vert')):
            continue
        src = os.path.join(sdir, name)
        out = src + '.qsb'
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(src):
            continue
        subprocess.run([qsb, '--glsl', '100es,120,150', '--hlsl', '50', '--msl', '12',
                        '-o', out, src], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port', default=os.environ.get('KGM_PORT', '/dev/ttyUSB0'))
    ap.add_argument('--hz', type=float, default=30.0, help='taxa de leitura dos canais')
    ap.add_argument('--gpu', choices=['auto', 'nvidia', 'default'], default='auto')
    ap.add_argument('--api', choices=['opengl', 'vulkan'], default='opengl')
    a = ap.parse_args()

    select_gpu(a.gpu, a.api)
    build_shaders()

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from gui_backend import ConfigEditor, EcuWorker, Live, TableEditor, renderer_name

    app = QGuiApplication(sys.argv)
    app.setApplicationName('KGM Painel')

    live = Live(renderer_name(a.api))
    worker = EcuWorker(a.port, a.hz)
    worker.frame.connect(live.on_frame)
    worker.link.connect(live.on_link)

    editor = TableEditor(worker, live)
    config = ConfigEditor(worker, live)

    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('live', live)
    engine.rootContext().setContextProperty('editor', editor)
    engine.rootContext().setContextProperty('config', config)
    engine.load(QUrl.fromLocalFile(os.path.join(HERE, 'qml', 'Main.qml')))
    if not engine.rootObjects():
        return 1
    live.watch_window(engine.rootObjects()[0])

    worker.start()
    try:
        return app.exec()
    finally:
        worker.requestInterruption()
        worker.wait(3000)


if __name__ == '__main__':
    sys.exit(main())
