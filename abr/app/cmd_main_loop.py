import argparse
import os.path

import wx

from abr.parsers import registry
from abr.frame import PersistentFrame, create_presenter

from . import add_default_arguments


def main():
    parser = argparse.ArgumentParser("abr_loop")
    add_default_arguments(parser)
    parser.add_argument('dirnames', nargs='*')
    parser.add_argument('--list', action='store_true')
    options = parser.parse_args()

    app = wx.App(False)

    for dirname in options.dirnames:
        unprocessed = registry.find_unprocessed(dirname, options)
        for filename, frequency in unprocessed:
            if options.list:
                print(filename, frequency)
            else:
                for model in registry.load(filename, options, [frequency]):
                    frame = PersistentFrame('ABR loop')
                    name = '%.2f kHz %s' % (model.freq, os.path.basename(filename))
                    frame.SetTitle(name)
                    presenter = create_presenter(model, frame, options, app)
                    frame.Show()
                    app.MainLoop()
                    frame.Close()
