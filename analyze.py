#!python

# wxPython has a lot of DeprecationWarnings so we ignore these
#import warnings; warnings.simplefilter('ignore', DeprecationWarning)

from optparse import OptionParser
from frame import PhysiologyFrame
import wx

#----------------------------------------------------------------------------

if __name__ == '__main__':
    parser = OptionParser("analyze.py [options] [filenames]")

    parser.add_option('--nofilter', action='store_false', dest='filter',
                      default=True, help='Do not filter waveform')
    parser.add_option('--lowpass', action='store', dest='lowpass',
                      help='Lowpass cutoff (Hz), default 10,000 Hz', default=10e3, type="float")
    parser.add_option('--highpass', action='store', dest='highpass',
                      help='Highpass cutoff (Hz), default 200 Hz', default=200, type="float")
    parser.add_option('--order', action='store', dest='order',
                      help='Filter order, default 1st order', default=1,
                      type='int')
    parser.add_option('-d', '--directory', action='store', dest='directory',
                      help='Default directory for files')
    parser.add_option('-i', '--invert', action='store_true', dest='invert',
                      default=False, 
                      help="Invert waveform polarity when waveforms are loaded")

    options, files = parser.parse_args()

    app = wx.PySimpleApp(0)
    frame = PhysiologyFrame(options)
    frame._nb.load(files)
    app.MainLoop()
