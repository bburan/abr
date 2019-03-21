import glob
import os.path
from pathlib import Path

import numpy as np
import pandas as pd

from abr.datatype import ABRWaveform, ABRSeries


base_template = 'ABR -1.0ms to 9.0ms{}average waveforms.csv'
nofilter_template = base_template.format(' ')
filter_template = base_template.format(' with {:.0f}Hz to {:.0f}Hz filter ')


def get_filename(pathname, filter_settings):
    if filter_settings is not None:
        filename = filter_template.format(
            filter_settings['highpass'],
            filter_settings['lowpass'])
    else:
        filename = nofilter_template

    if pathname.name == filename:
        return pathname
    else:
        return pathname / filename


def load(base_directory, filter_settings=None, frequencies=None):
    filename = get_filename(base_directory, filter_settings)
    if frequencies is not None and np.isscalar(frequencies):
        frequencies = [frequencies]

    data = pd.io.parsers.read_csv(filename, header=[0, 1], index_col=0).T
    fs = np.mean(np.diff(data.columns.values)**-1)
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


def get_frequencies(filename, filter_settings):
    data = pd.io.parsers.read_csv(filename, header=[0, 1], index_col=0).T
    frequencies = np.unique(data.index.get_level_values('frequency'))
    return frequencies.astype('float')


def find_all(dirname, filter_settings):
    results = []
    for pathname in Path(dirname).glob('*abr*'):
        if pathname.is_dir() :
            filename = get_filename(pathname, filter_settings)
            for frequency in get_frequencies(filename, filter_settings):
                results.append((filename, frequency))
    return results
