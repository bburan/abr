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

import importlib
import re
from glob import glob
import os
from pathlib import Path
import time

import pandas as pd
import numpy as np

from ..datatype import Point

P_ANALYZER = re.compile('.*kHz(?:-(\w+))?-analyzed.txt')


def get_analyzer(filename):
    return P_ANALYZER.match(filename.name).group(1)


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


def parse_peaks(peaks, threshold):
    # Convert the peaks dataframe to a format that can be used by _set_points.
    p_pattern = re.compile('P(\d) Latency')
    n_pattern = re.compile('N(\d) Latency')

    p_latencies = {}
    n_latencies = {}

    for c in peaks:
        match = p_pattern.match(c)
        if match:
            wave = int(match.group(1))
            p_latencies[wave] = pd.DataFrame({'x': peaks[c]})
        match = n_pattern.match(c)
        if match:
            wave = int(match.group(1))
            n_latencies[wave] = pd.DataFrame({'x': peaks[c]})

    p_latencies = pd.concat(p_latencies.values(), keys=p_latencies.keys(),
                            names=['wave'])
    p_latencies = {g: df.reset_index('Level', drop=True) \
                   for g, df in p_latencies.groupby('Level')}
    n_latencies = pd.concat(n_latencies.values(), keys=n_latencies.keys(),
                            names=['wave'])
    n_latencies = {g: df.reset_index('Level', drop=True) \
                   for g, df in n_latencies.groupby('Level')}

    for level, df in p_latencies.items():
        if level < threshold:
            df[:] = -df[:]

    for level, df in n_latencies.items():
        if level < threshold:
            df[:] = -df[:]

    return p_latencies, n_latencies


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

    def load(self, filename, frequencies=None):
        return self._module.load(filename, self._filter_settings, frequencies)

    def load_analysis(self, series, filename):
        freq, th, peaks = load_analysis(filename)
        series.threshold = th
        p_latencies, n_latencies = parse_peaks(peaks, th)
        series._set_points(p_latencies, Point.PEAK)
        series._set_points(n_latencies, Point.VALLEY)

    def find_analyzed_files(self, filename, frequency):
        frequency = round(frequency * 1e-3, 8)
        glob_pattern = self.filename_template.format(
            filename=filename.with_suffix(''),
            frequency=frequency,
            user='*')
        path = Path(glob_pattern)
        return list(path.parent.glob(path.name))

    def get_save_filename(self, filename, frequency):
        # Round frequency to nearest 8 places to minimize floating-point
        # errors.
        user_name = self._user + '-' if self._user else ''
        frequency = round(frequency * 1e-3, 8)
        save_filename = self.filename_template.format(
            filename=filename.with_suffix(''),
            frequency=frequency,
            user=user_name)
        return Path(save_filename)

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
                                 frequency=model.freq*1e-3,
                                 filter_history=filter_history,
                                 columns=columns,
                                 spreadsheet=spreadsheet)

        filename = self.get_save_filename(model.filename, model.freq)
        with open(filename, 'w') as fh:
            fh.writelines(content)

    def find_all(self, dirname, frequencies=None):
        result = self._module.find_all(dirname, self._filter_settings)
        if frequencies is not None:
            if np.isscalar(frequencies):
                frequencies = [frequencies]
            result = [(p, f) for (p, f) in result if f in frequencies]
        return result

    def find_processed(self, dirname, frequencies=None):
        return [(p, f) for p, f in self.find_all(dirname, frequencies) \
                if self.get_save_filename(p, f).exists()]

    def find_unprocessed(self, dirname, frequencies=None):
        return [(p, f) for p, f in self.find_all(dirname, frequencies) \
                if not self.get_save_filename(p, f).exists()]

    def find_analyses(self, dirname, frequencies=None):
        analyzed = {}
        for p, f in self.find_all(dirname, frequencies):
            analyzed[p, f] = self.find_analyzed_files(p, f)
        return analyzed

    def load_analyses(self, dirname, frequencies=None):
        analyzed = self.find_analyses(dirname, frequencies)
        keys = []
        thresholds = []
        for (raw_file, frequency), analyzed_files in analyzed.items():
            for analyzed_file in analyzed_files:
                user = get_analyzer(analyzed_file)
                keys.append((raw_file, frequency, analyzed_file, user))
                _, threshold, _ = load_analysis(analyzed_file)
                thresholds.append(threshold)

        cols = ['raw_file', 'frequency', 'analyzed_file', 'user']
        index = pd.MultiIndex.from_tuples(keys, names=cols)
        return pd.Series(thresholds, index=index)


CONTENT = '''
Threshold (dB SPL): {threshold:.2f}
Frequency (kHz): {frequency:.2f}
Filter history (zpk format): {filter_history}
NOTE: Negative latencies indicate no peak
{columns}
{spreadsheet}
'''.strip()


PARSER_MAP = {
    'PSI': 'psiexperiment',
    'EPL': 'EPL CFTS',
    'NCRAR': 'IHS text export',
}
