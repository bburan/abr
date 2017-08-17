import glob
import os.path

import tables
import numpy as np

from abr.datatype import ABRWaveform, ABRSeries


def load(fname, filter=None, abr_window=8.5e-3, frequencies=None):
    with tables.open_file(fname) as fh:
        fs = fh.root.waveforms._v_attrs['fs']
        cutoff = int(abr_window*fs)
        signal = fh.root.waveforms[:, :, :cutoff]*1e6
        levels = fh.root.trial_log.read(field='level')
        available_frequencies = fh.root.trial_log.read(field='frequency')

        # Load all frequencies by default
        if frequencies is None:
            frequencies = np.unique(available_frequencies)

        series = []
        for frequency in frequencies:
            mask = available_frequencies == frequency
            waveforms = [ABRWaveform(fs, s, l, filter=filter, min_latency=2)
                         for s, l in zip(signal[mask], levels[mask])]
            s = ABRSeries(waveforms, frequency/1e3)
            s.filename = fname
            series.append(s)
        return series


def get_frequencies(filename):
    with tables.open_file(filename) as fh:
        frequencies = fh.root.trial_log.read(field='frequency')
        return np.unique(frequencies)


def is_processed(filename, frequency, options):
    from abr.parsers import registry
    filename = registry.get_save_filename(filename, frequency, options)
    return os.path.exists(filename)


def find_unprocessed(dirname, options):
    wildcard = os.path.join(dirname, '*ABR*.hdf5')
    unprocessed = []
    for filename in glob.glob(wildcard):
        for frequency in get_frequencies(filename):
            if not is_processed(filename, frequency*1e-3, options):
                unprocessed.append((filename, frequency))
    return unprocessed
