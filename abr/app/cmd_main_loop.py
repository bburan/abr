from collections import Counter
import enaml
from enaml.qt.qt_application import QtApplication

import argparse
import os.path

from abr.parsers import registry

from . import add_default_arguments


with enaml.imports():
    from abr.main_window import SerialWindow
    from abr.presenter import SerialWaveformPresenter


def main():
    parser = argparse.ArgumentParser("abr_loop")
    add_default_arguments(parser)
    parser.add_argument('dirnames', nargs='*')
    parser.add_argument('--list', action='store_true')
    options = parser.parse_args()

    unprocessed = []
    for dirname in options.dirnames:
        unprocessed.extend(registry.find_unprocessed(dirname, options))

    if options.list:
        counts = Counter(f for f, _ in unprocessed)
        for filename, n in counts.items():
            filename = os.path.basename(filename)
            print(f'{filename} ({n})')

    else:
        app = QtApplication()
        presenter = SerialWaveformPresenter(unprocessed=unprocessed,
                                            options=options)
        view = SerialWindow(presenter=presenter)
        view.show()
        app.start()
        app.stop()
