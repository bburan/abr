import numpy as np
import re
import io

from abr.datatype import ABRWaveform, ABRSeries


def load(fname, invert=False, filter=None):
    with io.open(fname, encoding='ISO-8859-1') as f:
        line = f.readline()
        if not line.startswith(':RUN-'):
            raise IOError('Unsupported file format')

    p_level = re.compile(':LEVELS:([0-9;]+)')
    p_fs = re.compile('SAMPLE \(.sec\): ([0-9]+)')
    p_freq = re.compile('FREQ: ([0-9\.]+)')

    abr_window = 8500  # usec
    try:
        with io.open(fname, encoding='ISO-8859-1') as f:
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
            data = data.reshape(len(data)/len(levels), len(levels)).T
            data = data[:, :cutoff]

            waveforms = []
            for signal, level in zip(data, levels):
                # Checks for a ABR I-O bug that sometimes saves zeroed waveforms
                if not (signal == 0).all():
                    # Add new dimension to signal since the updated ABR program
                    # now takes individual waveforms.
                    waveform = ABRWaveform(fs, signal[np.newaxis], level,
                                           invert=invert, filter=filter)
                    waveforms.append(waveform)

            series = ABRSeries(waveforms, frequency)
            series.filename = fname
            return [series]

    except (AttributeError, ValueError):
        msg = 'Could not parse %s.  Most likely not a valid ABR file.' % fname
        raise IOError(msg)
