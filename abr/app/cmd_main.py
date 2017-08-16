#!python
import argparse
import wx
import pkg_resources

from abr.frame import PhysiologyFrame
from . import add_default_arguments


def main():
    parser = argparse.ArgumentParser("abr_gui")
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')

    options = parser.parse_args()

    app = wx.App(False)
    frame = PhysiologyFrame(options)
    if options.demo:
        files = [
            pkg_resources.resource_filename('abr', 'data/ABR-52-3'),
            pkg_resources.resource_filename('abr', 'data/CAP-139-5'),
        ]
        frame._nb.load(files)
    else:
        frame._nb.load(options.filenames)
    app.MainLoop()
