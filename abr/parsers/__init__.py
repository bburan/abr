'''
This module defines the import/export routines for interacting with the data
store.  If you wish to customize this, simply define the load() function.

load(run_location, invert, filter) -- When the program needs a run loaded, it
will pass the run_location provided by list().  Invert is a boolean flag
indicating whether waveform polarity should be flipped.  Filter is a dictionary
containing the following keys:
    1. ftype: any of None, butterworth, bessel, etc.
    2. fh: highpass cutoff (integer in Hz)
    3. fl: lowpass cutoff (integer in Hz)
All objects of the epl.datatype.Waveform class will accept the filter
dictionary and perform the appropriate filtering.  It is recommended you use the
filtering provided by the Waveform class as the parameters of the filter will
also be recorded.  This function must return an object of the
epl.datatype.ABRSeries class.  See this class for appropriate documentation.

The save function must return a message.  If there is an error in saving, throw
the appropriate exception.
'''

N_WAVES = 1

import re
import os
import time

import pkgutil
import importlib


import pandas as pd
import numpy as np

from ..datatype import WaveformPoint


def waveform_string(waveform):
    data = ['%.2f' % waveform.level]
    data.append('%f' % waveform.stat((0, 1), np.average))
    data.append('%f' % waveform.stat((0, 1), np.std))
    for i in range(1, N_WAVES+1):
        data.append('%.8f' % waveform.points[(WaveformPoint.PEAK, i)].latency)
        data.append('%.8f' % waveform.points[(WaveformPoint.PEAK, i)].amplitude)
        data.append('%.8f' % waveform.points[(WaveformPoint.VALLEY, i)].latency)
        data.append('%.8f' %
                    waveform.points[(WaveformPoint.VALLEY, i)].amplitude)
    return '\t'.join(data)


def filter_string(waveform):
    header = 'Filter history (zpk format):'
    if getattr(waveform, '_zpk', None) is None:
        return header + ' No filtering'
    else:
        t = 'Pass %d -- z: %r, p: %r, k: %r'
        filt = [t % (i, z, p, k) for i, (z, p, k) in enumerate(waveform._zpk)]
        return header + '\n' + '\n'.join(filt)


def load_analysis(fname):
    th_match = re.compile('Threshold \(dB SPL\): ([\w.]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)')
    with open(fname) as f:
        text = f.read()
        th = th_match.search(text).group(1)
        th = None if th == 'None' else float(th)
        freq = float(freq_match.search(text).group(1))
    data = pd.io.parsers.read_csv(fname, sep='\t', skiprows=5,
                                  index_col='Level')
    return (freq, th, data)


class ParserRegistry(object):

    def __init__(self):
        self.parsers = []

    def register(self, parser):
        self.parsers.append(parser)

    def load_file(self, filename, options):
        if options.filter:
            filter_settings = {
                'ftype': 'butter',
                'lowpass': options.lowpass,
                'highpass': options.highpass,
                'order': options.order,
            }
        else:
            filter_settings = None

        for parser in self.parsers:
            try:
                return parser.load(filename, filter_settings)
            except Exception as e:
                pass
        else:
            raise IOError('Unable to parse file')

    def save(self, model):
        filename = model.filename + '-{}kHz-analyzed.txt'.format(model.freq)
        header = 'Threshold (dB SPL): %r\nFrequency (kHz): %.2f\n%s\n%s\n%s\n%s'
        mesg = 'NOTE: Negative latencies indicate no peak'
        # Assume that all waveforms were filtered identically
        filters = filter_string(model.waveforms[-1])

        col_label_fmt = 'P%d Latency\tP%d Amplitude\tN%d Latency\tN%d Amplitude\t'
        col_labels = ['Level\t1msec Avg\t1msec StDev\t']
        col_labels.extend([col_label_fmt % (i, i, i, i) for i in range(1, N_WAVES+1)])
        col_labels = ''.join(col_labels)
        spreadsheet = '\n'.join([waveform_string(w) for w in
                                reversed(model.waveforms)])
        content = header % (model.threshold, model.freq, filters, mesg,
                            col_labels, spreadsheet)

        with open(filename, 'w') as fh:
            fh.writelines(content)

        return 'Saved data to %s' % filename

    def list_files(self, dirname):
        files = []
        for parser in self.parsers:
            if hasattr(parser, 'list_files'):
                files.extend(parser.list_files(dirname))
        return files


registry = ParserRegistry()


for loader, module_name, is_pkg in  pkgutil.walk_packages(__path__):
    try:
        module = loader.find_module(module_name).load_module(module_name)
        if hasattr(module, 'load'):
            registry.register(module)
    except ImportError:
        pass
