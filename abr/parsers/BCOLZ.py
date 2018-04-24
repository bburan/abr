import glob
import os.path

import numpy as np

from abr.datatype import ABRWaveform, ABRSeries
from abr.parsers import psi_bcolz



def load(filename, filter=None, abr_window=8.5e-3, frequencies=None):
    fh = psi_bcolz.load(filename)
    fs = fh.fs
    cutoff = int(round(abr_window*fs))
    groups = fh.get_epoch_groups('frequency', 'level')

    frequency_set = []
    for frequency, f_group in groups.groupby(level='frequency'):
        if frequencies is not None and not frequency in frequencies:
            continue
        waveforms = []
        for (_, level), epochs in f_group.iteritems():
            epochs = epochs[..., :cutoff]
            waveform = ABRWaveform(fh.fs, epochs, level, filter=filter,
                                   min_latency=1)
            waveforms.append(waveform)
        series = ABRSeries(waveforms, frequency*1e-3)
        series.filename = filename
        frequency_set.append(series)
    return frequency_set


def get_frequencies(filename):
    fh = psi_bcolz.load(filename)
    counts = fh.count_trials('frequency')
    return counts.index.values


def is_processed(filename, frequency, options):
    from abr.parsers import registry
    filename = registry.get_save_filename(filename, frequency, options)
    return os.path.exists(filename)


def find_unprocessed(dirname, options):
    wildcard = os.path.join(dirname, '*abr*')
    unprocessed = []
    for filename in glob.glob(wildcard):
        if not os.path.isdir(filename):
            continue
        try:
            for frequency in get_frequencies(filename):
                if not is_processed(filename, frequency*1e-3, options):
                    unprocessed.append((filename, frequency))
        except:
            print('Unable to read file', filename)
    return unprocessed
