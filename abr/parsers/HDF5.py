import glob
import os.path

import tables
import numpy as np

from abr.datatype import ABRWaveform, ABRSeries


def load(fname, filter=None, abr_window=8.5e-3):
    with tables.open_file(fname) as fh:
        fs = fh.root.waveforms._v_attrs['fs']
        cutoff = int(abr_window*fs)
        signal = fh.root.waveforms[:, :, :cutoff]*1e6
        levels = fh.root.trial_log.read(field='level')
        frequencies = fh.root.trial_log.read(field='frequency')

        series = []
        kw = dict(filter=filter)
        for f in np.unique(frequencies):
            m = frequencies == f
            waveforms = [ABRWaveform(fs, s, l, filter=filter, min_latency=2)
                         for s, l in zip(signal[m], levels[m])]
            s = ABRSeries(waveforms, f/1e3)
            s.filename = fname
            series.append(s)
        return series


def list_files(dirname):
    wildcard = os.path.join(dirname, '*ABR.hdf5')
    return glob.glob(wildcard)
