from __future__ import division

import pandas as pd
import numpy as np

from abr.datatype import ABRWaveform, ABRSeries


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

# Minimum wave 1 latencies
latencies = {
    1000: 3.1,
    3000: 2.1,
    4000: 2.3,
    6000: 1.8,
}

def load(fname, filter=None, abr_window=8.5e-3):
    with open(fname) as fh:
        line = fh.readline()
        if not line.startswith('Identifier:'):
            raise IOError('Unsupported file format')
    info = load_metadata(fname)
    info = info[info.channel == 1]
    fs = 1/(info.iloc[0]['smp. period']*1e-6)
    series = []
    for frequency, f_info in info.groupby('stim. freq.'):
        signal = load_waveforms(fname, f_info)
        signal = signal[signal.index >= 0]
        waveforms = []
        min_latency = latencies.get(frequency)
        for i, row in f_info.iterrows():
            s = signal[i].values[np.newaxis]
            waveform = ABRWaveform(fs, s, row['level'], min_latency=min_latency,
                                   filter=filter)
            waveforms.append(waveform)

        s = ABRSeries(waveforms, frequency/1e3)
        s.filename = fname
        series.append(s)
    return series
