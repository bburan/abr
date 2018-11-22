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

import re
import os
import time

import importlib

import pandas as pd
import numpy as np

from ..datatype import Point


def waveform_string(waveform):
    data = [f'{waveform.level:.2f}']
    data.append(f'{waveform.mean(0, 1)}')
    data.append(f'{waveform.std(0, 1)}')
    for _, point in sorted(waveform.points.items()):
        data.append(f'{point.latency:.8f}')
        data.append(f'{point.amplitude:.8f}')
    return '\t'.join(data)


def filter_string(waveform):
    if getattr(waveform, '_zpk', None) is None:
        return 'No filtering'
    t = 'Pass %d -- z: %r, p: %r, k: %r'
    filt = [t % (i, z, p, k) for i, (z, p, k) in enumerate(waveform._zpk)]
    return '\n' + '\n'.join(filt)


def load_analysis(fname):
    th_match = re.compile('Threshold \(dB SPL\): ([\w.]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)')
    with open(fname) as fh:
        text = fh.readline()
        th = th_match.search(text).group(1)
        th = None if th == 'None' else float(th)
        text = fh.readline()
        freq = float(freq_match.search(text).group(1))

        for line in fh:
            if line.startswith('NOTE'):
                break
        data = pd.io.parsers.read_csv(fh, sep='\t', index_col='Level')
    return (freq, th, data)


class Parser(object):

    filename_template = '{filename}-{frequency}kHz-{user}analyzed.txt'

    def __init__(self, file_format, filter_settings, user=None):
        '''
        Parameters
        ----------
        file_format : string
            File format that will be loaded.
        filter_settings : {None, dict}
            If None, no filtering is applied. If dict, must contain ftype,
            lowpass, highpass and order as keys.
        user : {None, string}
            Person analyzing the data.
        '''
        self._file_format = file_format
        self._filter_settings = filter_settings
        self._user = user
        self._module_name = f'abr.parsers.{file_format}'
        self._module = importlib.import_module(self._module_name)

    def load(self, filename, frequencies=None, include_analysis=True):
        data = self._module.load(filename, self._filter_settings, frequencies)
        if include_analysis:
            for series in data:
                analyzed_filename = self.get_save_filename(series.filename,
                                                           series.freq)
                if os.path.exists(analyzed_filename):
                    freq, th, peaks = load_analysis(analyzed_filename)
                    series.threshold = th
        return data

    def get_save_filename(self, filename, frequency):
        # Round frequency to nearest 8 places to minimize floating-point
        # errors.
        user_name = self._user + '-' if self._user else ''
        frequency = round(frequency, 8)
        return self.filename_template.format(filename=filename,
                                             frequency=frequency,
                                             user=user_name)

    def save(self, model):
        # Assume that all waveforms were filtered identically
        filter_history = filter_string(model.waveforms[-1])

        # Generate list of columns
        columns = ['Level', '1msec Avg', '1msec StDev']
        point_keys = sorted(model.waveforms[0].points)
        for point_number, point_type in point_keys:
            point_type_code = 'P' if point_type == Point.PEAK else 'N'
            for measure in ('Latency', 'Amplitude'):
                columns.append(f'{point_type_code}{point_number} {measure}')

        columns = '\t'.join(columns)
        spreadsheet = '\n'.join(waveform_string(w) \
                                for w in reversed(model.waveforms))
        content = CONTENT.format(threshold=model.threshold,
                                 frequency=model.freq,
                                 filter_history=filter_history,
                                 columns=columns,
                                 spreadsheet=spreadsheet)

        filename = self.get_save_filename(model.filename, model.freq)
        with open(filename, 'w') as fh:
            fh.writelines(content)

    def find_unprocessed(self, dirname, skip_errors=False):
        return self._module.find_unprocessed(dirname, self, skip_errors)


CONTENT = '''
Threshold (dB SPL): {threshold:.2f}
Frequency (kHz): {frequency:.2f}
Filter history (zpk format): {filter_history}
NOTE: Negative latencies indicate no peak
{columns}
{spreadsheet}
'''.strip()
