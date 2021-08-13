import glob
import json
import os.path
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

from abr.datatype import ABRWaveform, ABRSeries


def get_filename(pathname):
    filename = 'ABR average waveforms.csv'
    if pathname.name == filename:
        return pathname
    return pathname / filename


def load(base_directory, filter_settings=None, frequencies=None):
    filename = get_filename(base_directory)
    with filename.open() as fh:
        fh.readline() # frequency
        fh.readline() # level
        has_metadata = fh.readline().startswith('epoch_n')

    if frequencies is not None and np.isscalar(frequencies):
        frequencies = [frequencies]

    if has_metadata:
        data = pd.io.parsers.read_csv(filename, header=[0, 1, 2, 3], index_col=0).T
        data = data.reset_index(['epoch_n', 'epoch_reject_ratio'], drop=True)
        settings_file = filename.parent / 'ABR processing settings.json'
        fs = json.loads(settings_file.read_text())['actual_fs']
        print(fs)
    else:
        data = pd.io.parsers.read_csv(filename, header=[0, 1], index_col=0).T
        fs = np.mean(np.diff(data.columns.values)**-1)
    if filter_settings is not None:
        Wn = filter_settings['highpass'], filter_settings['lowpass']
        N = filter_settings['order']
        b, a = signal.iirfilter(N, Wn, fs=fs)
        data_filt = signal.filtfilt(b, a, data.values, axis=-1)
        data = pd.DataFrame(data_filt, columns=data.columns, index=data.index)

    data.columns *= 1e3
    waveforms = {}

    for (frequency, level), w in data.iterrows():
        frequency = float(frequency)
        level = float(level)
        if frequencies is not None:
            if frequency not in frequencies:
                continue
        frequency = float(frequency)
        level = float(level)
        waveform = ABRWaveform(fs, w, level)
        waveforms.setdefault(frequency, []).append(waveform)

    series = []
    for frequency, stack in waveforms.items():
        s = ABRSeries(stack, frequency)
        s.filename = filename
        s.id = filename.parent.name
        series.append(s)

    return series


def get_frequencies(filename):
    data = pd.io.parsers.read_csv(filename, header=[0, 1], index_col=0).T
    frequencies = np.unique(data.index.get_level_values('frequency'))
    return frequencies.astype('float')


def find_all(dirname, frequencies=None):
    results = []
    for pathname in Path(dirname).glob('*abr*'):
        if pathname.is_dir() :
            filename = get_filename(pathname)
            for frequency in get_frequencies(filename):
                if frequencies is not None and frequency not in frequencies:
                    continue
                results.append((filename, frequency))
    return results
