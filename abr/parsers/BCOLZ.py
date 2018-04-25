import glob
import os.path

import numpy as np

from abr.datatype import ABRWaveform, ABRSeries
from abr.parsers import psi_bcolz



def load(filename, filter=None, abr_window=8.5e-3, frequencies=None):
    fh = psi_bcolz.load(filename)
    fs = fh.fs
    cutoff = int(round(abr_window*fs))
    reject_threshold = fh.trial_log.at[0, 'reject_threshold']

    counts = fh.count_epochs_combined_polarity(['frequency', 'level'])
    groups = counts.index.tolist()

    waveforms = {}

    signal_filter = {
        'order': filter['order'],
        'fl': filter['highpass'],
        'fh': filter['lowpass'],
        'ftype': filter['ftype'],
        'btype': 'band',
    }

    for frequency, level in groups:
        trial_filter = {'frequency': frequency, 'level': level}
        epochs = fh.get_epochs_combined_polarity(trial_filter,
                                                 reject_threshold=reject_threshold,
                                                 signal_filter=signal_filter)
        waveform = ABRWaveform(fh.fs, epochs, level, min_latency=0.5)
        waveforms.setdefault(frequency, []).append(waveform)

    series_set = []
    for frequency, waveforms in waveforms.items():
        series = ABRSeries(waveforms, frequency*1e-3)
        series.filename = filename
        series_set.append(series)
    return series_set


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
