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

import abr
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
    th_match = re.compile('Threshold \(dB SPL\): ([\w.-]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)|Stimulus: ([.\w]+)?')
    with open(fname) as fh:
        text = fh.readline()
        th = th_match.search(text).group(1)
        th = None if th == 'None' else float(th)
        text = fh.readline()

        match = freq_match.search(text)
        if match.group(1) is not None:
            freq = float(match.group(1))
        else:
            freq = match.group(2)
            if freq == 'click':
                freq = -1
            else:
                freq = float(freq)

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
        self._rater = user
        self._module_name = f'abr.parsers.{file_format}'
        self._module = importlib.import_module(self._module_name)

    def load(self, fs):
        return fs.get_series(self._filter_settings)

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

        if model.freq == -1:
            stimulus = 'Stimulus: click'
        else:
            stimulus = f'Stimulus: {model.freq*1e-3:.2f} kHz'

        content = CONTENT.format(threshold=model.threshold,
                                 stimulus=stimulus,
                                 filter_history=filter_history,
                                 columns=columns,
                                 spreadsheet=spreadsheet,
                                 version=abr.__version__)


        filename = model.dataset.get_analyzed_filename(self._rater)
        with open(filename, 'w') as fh:
            fh.writelines(content)

    def iter_all(self, path):
        yield from self._module.iter_all(path)

    def find_processed(self, path):
        for ds in self.iter_all(path):
            if Path(ds.get_analyzed_filename(self._rater).exists()):
                yield ds

    def find_unprocessed(self, path):
        for ds in self.iter_all(path):
            if not Path(ds.get_analyzed_filename(self._rater)).exists():
                yield ds

    def find_analyses(self, study_directory):
        analyzed = {}
        for ds in self.iter_all(study_directory):
            analyzed[ds] = ds.find_analyzed_files()
        return analyzed

    def load_analyses(self, study_directory):
        keys = []
        thresholds = []
        waves = []
        analyses = self.find_analyses(study_directory)

        for ds, analyzed_filenames in analyses.items():
            for a in analyzed_filenames:
                _, th, w = load_analysis(a)
                parts = a.stem.split('-')
                if parts[-2].endswith('kHz'):
                    analyzer = 'Unknown'
                else:
                    analyzer = parts[-2]

                keys.append((ds, analyzer))
                thresholds.append(th)
                waves.append(w)

        names = ['dataset', 'analyzer']
        index = pd.MultiIndex.from_tuples(keys, names=names)
        thresholds = pd.Series(thresholds, index=index, name='thresholds').reset_index()
        waves = pd.concat(waves, keys=keys, names=names).reset_index()
        return thresholds, waves


CONTENT = '''
Threshold (dB SPL): {threshold:.2f}
{stimulus}
Filter history (zpk format): {filter_history}
file_format_version: 0.0.3
code_version: {version}
NOTE: Negative latencies indicate no peak. NaN for amplitudes indicate peak was unscorable.
{columns}
{spreadsheet}
'''.strip()


PARSER_MAP = {
    'PSI': 'psiexperiment',
    'NCRAR': 'IHS text export',
    'EPL': 'EPL CFTS',
}
