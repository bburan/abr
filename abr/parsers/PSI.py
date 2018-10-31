import os.path
import glob

import numpy as np
import pandas as pd

from abr.datatype import ABRWaveform, ABRSeries


base_template = 'ABR -1.0ms to 9.0ms{}average waveforms.csv'
nofilter_template = base_template.format(' ')
filter_template = base_template.format(' with {:.0f}Hz to {:.0f}Hz filter ')


def get_filename(base_directory, filter_settings):
    if filter_settings is not None:
        filename = filter_template.format(
            filter_settings['highpass'],
            filter_settings['lowpass'])
    else:
        filename = nofilter_template
    return os.path.join(base_directory, filename)


def load(base_directory, filter_settings=None, frequencies=None):

    filename = get_filename(base_directory, filter_settings)

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
        frequency = float(frequency)*1e-3
        level = float(level)
        stack = waveforms.setdefault(frequency, [])
        waveform = ABRWaveform(fs, w, level)
        stack.append(waveform)

    series = []
    for frequency, stack in waveforms.items():
        s = ABRSeries(stack, frequency)
        s.filename = filename[:-4]
        series.append(s)

    return series


def is_processed(base_directory, frequency, parser):
    filename = get_filename(base_directory, parser._filter_settings)[:-4]
    save_filename = parser.get_save_filename(filename, frequency)
    return os.path.exists(save_filename)


def get_frequencies(base_directory, filter_settings):
    filename = get_filename(base_directory, filter_settings)
    data = pd.io.parsers.read_csv(filename, header=[0, 1], index_col=0).T
    frequencies = np.unique(data.index.get_level_values('frequency'))
    return frequencies.astype('float')


def find_unprocessed(dirname, parser):
    wildcard = os.path.join(dirname, '*abr*')
    unprocessed = []
    for base_directory in glob.glob(wildcard):
        for frequency in get_frequencies(base_directory,
                                         parser._filter_settings):
            if not is_processed(base_directory, frequency*1e-3, parser):
                unprocessed.append((base_directory, frequency))
    return unprocessed
