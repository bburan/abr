import argparse

import enaml
from enaml.application import deferred_call
from enaml.qt.qt_application import QtApplication

import pkg_resources

from . import add_default_arguments
from abr.parsers import registry

with enaml.imports():
    from abr.main_window import DNDWindow, add_dock_item


def main():
    parser = argparse.ArgumentParser("abr_gui")
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parser.parse_args()

    app = QtApplication()
    view = DNDWindow(options=options)

    dock_area = view.find('dock_area')
    for filename in options.filenames:
        for model in registry.load(filename, options):
            deferred_call(add_dock_item, dock_area, model, filename, options)

    view.show()
    app.start()
    app.stop()
