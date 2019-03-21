import argparse
from pathlib import Path

import enaml
from enaml.application import deferred_call
from enaml.qt.qt_application import QtApplication

from . import add_default_arguments, parse_args
from abr.parsers import Parser

with enaml.imports():
    from abr.main_window import DNDWindow, load_files
    from abr.presenter import WaveformPresenter


def main():
    parser = argparse.ArgumentParser('abr_gui')
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parse_args(parser)

    app = QtApplication()
    view = DNDWindow(parser=options['parser'], latencies=options['latencies'])

    filenames = [(Path(f), None) for f in options['filenames']]

    deferred_call(load_files, options['parser'], options['latencies'],
                  filenames, view.find('dock_area'))

    view.show()
    app.start()
    app.stop()
