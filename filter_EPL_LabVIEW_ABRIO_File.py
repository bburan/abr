import re
import os
import io
from numpy import average, std, array
from datatype import WaveformPoint, ABRWaveform, ABRSeries
import time

abr_re = '^ABR-[0-9]+-[0-9]+(\\.dat)?$'
abr_processed_re = '^ABR-[0-9]+-[0-9]+(\\.dat)?-analyzed.txt$'
numbers = re.compile('[0-9]+')

'''
This module defines the import/export routines for interacting with the data
store.  If you wish to customize this, simply define the functions load(),
save(), list() and sort().

list(location, skip_processed) -- Accepts a location string (provided by the
-d flag or the user options dialog).  In the example below, the location
string is expected to be a directory, but possible variations include a
database connection string.  Skip_Processed is a boolean that indicates
whether or not already processed runs should be skipped (very useful when you
are running the program in automatic mode where the next run in the series is
loaded as soon as analysis of the current run is complete).  This function
should return a list of tuples where the tuple is in the format (name,
run_location).  Name is the string displayed to the user (e.g. 'BNB37 Right, Run
2 at 16kHz'), while run_location is can be any Python object that provides the
information needed by load() to access the data from that run.  It's up to you
to put sufficient information into the run_location variable to be able to find
the data for that specific run (e.g. if all data for the run is stored in a
file, then run_location would hold a pointer to the file).  The contents you put
into run_location will be passed to load, and you can use these contents to find
the data.

load(run_location, invert, filter) -- When the program needs a run loaded, it
will pass the run_location provided by list().  Invert is a boolean flag
indicating whether waveform polarity should be flipped.  Filter is a dictionary
containing the following keys:
    1. ftype: any of None, butterworth, bessel, etc.
    2. fh: highpass cutoff (integer in Hz)
    3. fl: lowpass cutoff (integer in Hz)
All objects of the epl.datatype.Waveform class will accept the filter
dictionary and perform the appropriate filtering.  It is recommended you use the
filtering provided by the Waveform class as the parameters of the filter will
also be recorded.  This function must return an object of the
epl.datatype.ABRSeries class.  See this class for appropriate documentation.

save(ABRseries) -- When the user requests to save the analyzed data, the data,
stored as an ABRseries object, is passed to save().  ABRseries contains the
following attributes:
      1. filename: name of the file that the data was originally loaded from
      2. freq: stimulus frequency
      3. series: a list of waveforms (in the ABRWaveform class format) that
      belong to the series.
Each waveform of the ABRWaveform class contains the following attributes:
      1. level: stimulus level
      2. zpk: a list containing the history of filtering for the waveform,
      stored as zpk format.  [0] is the earliest filtering, [-1] is the most
      recent.
      3. points: a dictionary containing the points P1-5 and N1-5.  Each point
      is an object with amplitude and latency attributes.

The save function must return a message.  If there is an error in saving, throw
the appropriate exception.
'''


def load(run, invert=False, filter=None):
    return loadabr(run, invert=invert, filter=filter)


def save(model):
    n = 5

    filename = model.filename + '-analyzed.txt'
    header = 'Threshold (dB SPL): %r\nFrequency (kHz): %.2f\n%s\n%s\n%s\n%s'
    mesg = 'NOTE: Negative latencies indicate no peak'
    # Assume that all waveforms were filtered identically
    filters = filter_string(model.waveforms[-1])

    # Prepare spreadsheet
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
    data.append('%f' % waveform.stat((0, 1), average))
    data.append('%f' % waveform.stat((0, 1), std))
    for i in range(1, 6):
        data.append('%.2f' % waveform.points[(WaveformPoint.PEAK, i)].latency)
        data.append('%.2f' % waveform.points[(WaveformPoint.PEAK, i)].amplitude)
        data.append('%.2f' % waveform.points[(WaveformPoint.VALLEY, i)].latency)
        data.append('%.2f' %
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


def loadabr(fname, invert=False, filter=None):
    p_level = re.compile(':LEVELS:([0-9;]+)')
    p_fs = re.compile('SAMPLE \(.sec\): ([0-9]+)')
    p_freq = re.compile('FREQ: ([0-9\.]+)')

    abr_window = 8500  # usec
    try:
        with io.open(fname, encoding='ISO-8859-1') as f:
            header, data = f.read().split('DATA')

            # Extract data from header
            levelstring = p_level.search(header).group(1).strip(';').split(';')
            levels = array(levelstring).astype(float)
            sampling_period = float(p_fs.search(header).group(1))
            frequency = float(p_freq.search(header).group(1))

            # Convert text representation of data to Numpy array
            fs = 1e6/sampling_period
            cutoff = abr_window / sampling_period
            data = array(data.split()).astype(float)
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
            return series

    except (AttributeError, ValueError):
        msg = 'Could not parse %s.  Most likely not a valid ABR file.' % fname
        raise IOError(msg)


def loadabranalysis(fname):
    th_match = re.compile('Threshold \(dB SPL\): ([\w.]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)')
    with open(fname) as f:
        text = f.read()
        th = th_match.search(text).group(1)
        th = None if th == 'None' else float(th)
        freq = float(freq_match.search(text).group(1))
    data = loadspreadsheet(fname, header=6)
    return (freq, th, data)
