#!python
import argparse
import wx
import pkg_resources

from abr.frame import PhysiologyFrame

def main():
    parser = argparse.ArgumentParser("abr_gui")

    parser.add_argument('--nofilter', action='store_false', dest='filter',
                        default=True, help='Do not filter waveform')
    parser.add_argument('--lowpass', action='store', dest='lowpass',
                        help='Lowpass cutoff (Hz), default 10,000 Hz',
                        default=10e3, type=float)
    parser.add_argument('--highpass', action='store', dest='highpass',
                        help='Highpass cutoff (Hz), default 200 Hz',
                        default=200, type=float)
    parser.add_argument('--order', action='store', dest='order',
                        help='Filter order, default 1st order', default=1,
                        type=int)
    parser.add_argument('-d', '--directory', action='store', dest='directory',
                        help='Default directory for files')
    parser.add_argument('-i', '--invert', action='store_true', dest='invert',
                        default=False,
                        help="Invert waveform polarity when loaded")
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
