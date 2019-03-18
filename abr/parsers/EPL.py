import io
from pathlib import Path
import re

import numpy as np
import pandas as pd
from scipy import signal

from abr.datatype import ABRWaveform, ABRSeries


def load(filename, filter=None, frequencies=None):
    filename = Path(filename)
    with filename.open(encoding='ISO-8859-1') as f:
        line = f.readline()
        if not line.startswith(':RUN-'):
            raise IOError('Unsupported file format')

    p_level = re.compile(':LEVELS:([0-9;]+)')
    p_fs = re.compile('SAMPLE \(.sec\): ([0-9]+)')
    p_freq = re.compile('FREQ: ([0-9\.]+)')


    abr_window = 8500  # usec
    try:
        with filename.open(encoding='ISO-8859-1') as f:
            header, data = f.read().split('DATA')

            # Extract data from header
            levelstring = p_level.search(header).group(1).strip(';').split(';')
            levels = np.array(levelstring).astype(np.float32)
            sampling_period = float(p_fs.search(header).group(1))
            frequency = float(p_freq.search(header).group(1))

            # Convert text representation of data to Numpy array
            fs = 1e6/sampling_period
            cutoff = int(abr_window / sampling_period)
            data = np.array(data.split()).astype(np.float32)
            data.shape = -1, len(levels)
            data = data.T[:, :cutoff]
            t = np.arange(data.shape[-1]) / fs * 1e3
            t = pd.Index(t, name='time')

            if filter is not None:
                Wn = filter['highpass']/(0.5*fs), filter['lowpass']/(0.5*fs)
                N = filter['order']
                b, a = signal.iirfilter(N, Wn)
                data = signal.filtfilt(b, a, data, axis=-1)

            waveforms = []
            for s, level in zip(data, levels):
                # Checks for a ABR I-O bug that sometimes saves zeroed waveforms
                if not (s == 0).all():
                    w = pd.Series(s, index=t)
                    waveform = ABRWaveform(fs, w, level)
                    waveforms.append(waveform)

            series = ABRSeries(waveforms, frequency)
            series.filename = filename
            return [series]

    except (AttributeError, ValueError):
        msg = 'Could not parse %s.  Most likely not a valid ABR file.' % fname
        raise IOError(msg)
