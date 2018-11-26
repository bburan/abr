import argparse

import enaml
from enaml.application import deferred_call
from enaml.qt.qt_application import QtApplication

from . import add_default_arguments, parse_args
from abr.parsers import Parser

with enaml.imports():
    from abr.main_window import DNDWindow, add_dock_item
    from abr.presenter import WaveformPresenter


def main():
    parser = argparse.ArgumentParser("abr_gui")
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parse_args(parser)

    app = QtApplication()
    view = DNDWindow(parser=options['parser'], latencies=options['latencies'])

    dock_area = view.find('dock_area')
    parser = options['parser']
    for filename in options['filenames']:
        for model in parser.load(filename):
            presenter = WaveformPresenter(options['parser'], options['latencies'])
            presenter.load(model)
            deferred_call(add_dock_item, dock_area, model, filename, presenter)

    view.show()
    app.start()
    app.stop()
