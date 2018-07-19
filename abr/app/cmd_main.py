import argparse

import enaml
from enaml.qt.qt_application import QtApplication

import pkg_resources

from . import add_default_arguments

with enaml.imports():
    from abr.main_window import DNDWindow


def main():
    parser = argparse.ArgumentParser("abr_gui")
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parser.parse_args()

    app = QtApplication()
    view = DNDWindow(options=options)
    view.show()
    app.start()
    app.stop()
