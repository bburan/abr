import argparse
import os.path

import wx

from abr.control import MatplotlibPanel
from abr.parsers import registry
from abr.presenter import WaveformPresenter
from abr.interactor import WaveformInteractor
from abr.frame import PersistentFrame

from . import add_default_arguments


def main():
    parser = argparse.ArgumentParser("abr_loop")
    add_default_arguments(parser)
    parser.add_argument('dirnames', nargs='*')
    options = parser.parse_args()

    app = wx.App(False)

    for dirname in options.dirnames:
        filenames = registry.list_files(dirname)
        for filename in filenames:
            for model in registry.load_file(filename, options):
                frame = PersistentFrame('ABR loop')
                view = MatplotlibPanel(frame, 'Time (msec)', 'Amplitude (uV)')
                interactor = WaveformInteractor()
                presenter = WaveformPresenter(model, view, interactor, app=app)
                name = '%.2f kHz %s' % (model.freq, os.path.basename(filename))
                frame.SetTitle(name)
                frame.Show()
                app.MainLoop()
                frame.Close()
