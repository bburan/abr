import re
import os
import time

import tables
import pandas as pd
import numpy as np

from datatype import WaveformPoint, ABRWaveform, ABRSeries

abr_re = '^ABR-[0-9]+-[0-9]+(\\.dat)?$'
abr_processed_re = '^ABR-[0-9]+-[0-9]+(\\.dat)?-analyzed.txt$'
numbers = re.compile('[0-9]+')


def load(run, invert=False, filter=None):
    return loadabr(run, invert=invert, filter=filter)


def save(model):
    n = 5

    filename = model.filename + '-{}kHz-analyzed.txt'.format(model.freq)
    header = 'Threshold (dB SPL): %r\nFrequency (kHz): %.2f\n%s\n%s\n%s\n%s'
    mesg = 'NOTE: Negative latencies indicate no peak'
    # Assume that all waveforms were filtered identically
    filters = filter_string(model.waveforms[-1])

    col_label_fmt = 'P%d Latency\tP%d Amplitude\tN%d Latency\tN%d Amplitude\t'
    col_labels = ['Level\t1msec Avg\t1msec StDev\t']
    col_labels.extend([col_label_fmt % (i, i, i, i) for i in range(1, n+1)])
    col_labels = ''.join(col_labels)
    spreadsheet = '\n'.join([waveform_string(w) for w in
                             reversed(model.waveforms)])
    header = header % (model.threshold, model.freq, filters, mesg, col_labels,
                       spreadsheet)

    f = safeopen(filename)
    f.writelines(header)
    f.close()

    return 'Saved data to %s' % filename


def waveform_string(waveform):
    data = ['%.2f' % waveform.level]
    data.append('%f' % waveform.stat((0, 1), np.average))
    data.append('%f' % waveform.stat((0, 1), np.std))
    for i in range(1, 6):
        data.append('%.8f' % waveform.points[(WaveformPoint.PEAK, i)].latency)
        data.append('%.8f' % waveform.points[(WaveformPoint.PEAK, i)].amplitude)
        data.append('%.8f' % waveform.points[(WaveformPoint.VALLEY, i)].latency)
        data.append('%.8f' %
                    waveform.points[(WaveformPoint.VALLEY, i)].amplitude)
    return '\t'.join(data)


def filter_string(waveform):
    header = 'Filter history (zpk format):'
    if waveform._zpk is None:
        return header + ' No filtering'
    else:
        templ = 'Pass %d -- z: %r, p: %r, k: %r'
        filt = [templ % (i, z, p, k) for i, (z, p, k)
                in enumerate(waveform._zpk)]
        return header + '\n' + '\n'.join(filt)


def safeopen(file):
    '''Checks to see if a file already exists.  If it does, it is archived
    using the earlier of the file creation time or the file modified time.  In
    my experience, the file creation time changes when the file is copied to a
    new filesystem; however, the file modified time usually is not updated on
    this copy.  Another complication is that Windows does not change the file
    creation time if the same filename is deleted and then recreated within a
    certain period.  We only use file modification time.

    '''
    if os.path.exists(file):
        base, fname = os.path.split(file)
        filetime = os.path.getmtime(file)
        filestring = time.strftime('%Y-%m-%d-%H-%M-%S-', time.gmtime(filetime))
        new_fname = os.path.join(base, filestring+fname)
        os.rename(file, new_fname)
    return open(file, 'w')


def loadabr(fname, invert=False, filter=None, abr_window=8.5e-3):
    with tables.open_file(fname) as fh:
        fs = fh.root.waveforms._v_attrs['fs']
        cutoff = int(abr_window*fs)
        signal = fh.root.waveforms[:, :, :cutoff]*1e6
        levels = fh.root.trial_log.read(field='level')
        frequencies = fh.root.trial_log.read(field='frequency')

        series = []
        kw = dict(invert=invert, filter=filter)
        for f in np.unique(frequencies):
            m = frequencies == f
            waveforms = [ABRWaveform(fs, s, l, **kw)
                         for s, l in zip(signal[m], levels[m])]
            s = ABRSeries(waveforms, f/1e3)
            s.filename = fname
            series.append(s)
        return series


def loadabranalysis(fname):
    th_match = re.compile('Threshold \(dB SPL\): ([\w.]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)')
    with open(fname) as f:
        text = f.read()
        th = th_match.search(text).group(1)
        th = None if th == 'None' else float(th)
        freq = float(freq_match.search(text).group(1))
    data = pd.io.parsers.read_csv(fname, sep='\t', skiprows=5,
                                  index_col='Level')
    return (freq, th, data)
