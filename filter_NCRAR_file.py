from __future__ import division

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

################################################################################
# Utility functions
################################################################################
def _parse_line(line):
    '''
    Parse list of comma-separated values from line

    Parameters
    ----------
    line : string
        Line containing the values that need to be parsed

    Returns
    -------
    tokens : list
        List of values found in line.  If values are numeric, they will be
        converted to floats.  Otherwise they will be returned as strings.
    '''
    tokens = line.strip().split(',')[1:]
    try:
        return [float(t) for t in tokens if t]
    except ValueError:
        return [t for t in tokens if t]


def load_metadata(filename):
    '''
    Load the metadata stored in the ABR file

    Parameters:
    -----------
    filename : string
        Filename to load

    Returns
    -------
    info : pandas.DataFrame
        Dataframe containing information on each waveform
    '''
    info = {}
    with open(filename, 'r') as fh:
        for i, line in enumerate(fh):
            if i == 20:
                break
            name = line.split(',', 1)[0].strip(':').lower()
            info[name] = _parse_line(line)
    info = pd.DataFrame(info)

    # Number the trials.  We will use this number later to look up which column
    # contains the ABR waveform for corresponding parameter.
    info['waveform'] = np.arange(len(info))
    info.set_index('waveform', inplace=True)

    # Convert the intensity to the actual level in dB SPL
    info['level'] = np.round(info.intensity/10)*10

    # Store the scaling factor for the waveform so we can recover this when
    # loading.  By default the scaling factor is 674. For 110 dB SPL, the
    # scaling factor is 337.  The statistician uses 6.74 and 3.37, but he
    # includes a division of 100 elsewhere in his code to correct.
    info['waveform_sf'] = 6.74e2

    # The rows where level is 110 dB SPL have a different scaling factor.
    info.loc[info.level == 110, 'waveform_sf'] = 3.37e2

    # Start time of stimulus in usec (since sampling period is reported in usec,
    # we should try to be consistent with all time units).
    info['stimulus_start'] = 12.5e3
    return info


def load_waveforms(filename, info):
    '''
    Load the waveforms stored in the ABR file

    Only the waveforms specified in info will be loaded.  For example, if you
    have filtered the info DataFrame to only contain waveforms from channel 1,
    only those waveforms will be loaded.

    Parameters:
    -----------
    filename : string
        Filename to load
    info : pandas.DataFrame
        Waveform metadata (see `load_metadata`)

    Returns
    -------
    info : pandas.DataFrame
        Dataframe containing waveforms

    '''
    # Read the waveform table into a dataframe
    df = pd.io.parsers.read_csv(filename, skiprows=20)

    # Keep only the columns containing the signal of interest.  There are six
    # columns for each trial.  We only want the column containing the raw
    # average (i.e., not converted to uV).
    df = df[[c for c in df.columns if c.startswith('Average:')]]

    # Renumber them so we can look them up by number.  The numbers should
    # correspond to the trial number we generated in `load_metadata`.
    df.columns = np.arange(len(df.columns))

    # Loop through the entries in the info DataFrame.  This dataframe contains
    # metadata needed for processing the waveform (e.g., it tells us which
    # waveforms to keep, the scaling factor to use, etc.).
    signals = []
    for w_index, w_info in info.iterrows():
        # Compute time of each point.  Currently in usec because smp. period is
        # in usec.
        t = np.arange(len(df), dtype=np.float32)*w_info['smp. period']
        # Subtract stimulus start so that t=0 is when stimulus begins.  Convert
        # to msec.
        t = (t-w_info['stimulus_start'])*1e-3
        time = pd.Index(t, name='time')

        # Divide by the scaling factor and convert from nV to uV
        s = df[w_index]/w_info['waveform_sf']*1e-3
        s.index = time
        signals.append(s)

    # Merge together the waveforms into a single DataFrame
    waveforms = pd.concat(signals, keys=info.index, names=['waveform'])
    waveforms = waveforms.unstack(level='waveform')
    return waveforms



################################################################################
# API
################################################################################
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
    if getattr(waveform, '_zpk', None) is None:
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
    info = load_metadata(fname)
    info = info[info.channel == 1]
    fs = 1/(info.iloc[0]['smp. period']*1e-6)
    print info.iloc[0]['smp. period']
    print fs
    series = []
    kw = dict(invert=invert, filter=None)
    for frequency, f_info in info.groupby('stim. freq.'):
        signal = load_waveforms(fname, f_info)
        signal = signal[signal.index >= 0]
        waveforms = []
        for i, row in f_info.iterrows():
            s = signal[i].values[np.newaxis]
            waveform = ABRWaveform(fs, s, row['level'], **kw)
            waveforms.append(waveform)
        s = ABRSeries(waveforms, frequency/1e3)
        s.filename = fname
        series.append(s)
    return series


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
