import re, os
from numpy import average
from numpy import std
from datatype import Point
from walker import ReWalker
from datafile import loadabr

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
    if filter['ftype'] == 'None':
        return loadabr(run, filter=False, invert=invert)
    else:
        return loadabr(run, filter=True, fdict=filter, invert=invert)

def list(location, skip_processed=False):
    if location is not None and os.path.isdir(location):
        data = os.listdir(location)
        return [{
            'display':  d,
            'data':     d,
            'sort_key': d,
            'has_children': os.path.isdir(os.path.join(location, d)),
            'data_string':  os.path.join(location, d),
            } for d in data]

    '''The walker class recursively iterates through all directories and returns
    a list of file paths (relative to the location directory) when list() is
    called.  ReWalker returns only files whose name matches the regex provided.
    '''
    '''
    runs = ReWalker(location, abr_re).list()
    if skip_processed:
        processed_runs = ReWalker(location, abr_processed_re).list()
        processed_runs = [os.path.split(p)[1][:-13] for p in processed_runs]
        runs = [r for r in runs if os.path.split(r)[1] not in processed_runs]
    '''

    '''The next three lines use a decorate-sort-undecorate paradigm where the
    file paths are turned into a list of tuples, with each tuple consisting of
    (sort_key, file_path).  When sort() is called on a list, it always sorts by
    the first element (the sort key in this case), then the second element and
    so on.  Once the list is sorted, we can then remove the sort key and return
    just the file paths.
    '''
    '''
    runs = [([int(n) for n in numbers.findall(r)], r) for r in runs]
    runs.sort()
    runs = [r[1] for r in runs]
    runs = [(os.path.split(r)[1], r) for r in runs]
    return runs
    '''

def save(model):
    n = 5

    filename = model.filename + '-analyzed.txt'
    header = 'Threshold (dB SPL): %r\nFrequency (kHz): %.2f\n%s\n%s\n%s\n%s'
    mesg = 'NOTE: Negative latencies indicate no peak'
    filters = filter_string(model.series[-1])

    #Prepare spreadsheet
    col_label_fmt = 'P%d Latency\tP%d Amplitude\tN%d Latency\tN%d Amplitude\t'
    col_labels = ['Level\t1msec Avg\t1msec StDev\t']
    col_labels.extend([col_label_fmt % (i,i,i,i) for i in range(1,n+1)])
    col_labels = ''.join(col_labels)
    spreadsheet = '\n'.join([waveform_string(w) for w in \
        reversed(model.series)])

    header = header % (model.threshold, model.freq, filters, mesg, col_labels,
            spreadsheet)

    f = safeopen(filename)
    f.writelines(header)
    f.close()

    return 'Saved data to %s' % filename

def waveform_string(waveform):
    data = ['%.2f' % waveform.level]
    data.append('%f' % waveform.stat((0,1), average))
    data.append('%f' % waveform.stat((0,1), std))
    for i in range(1,6):
        data.append('%.2f' % waveform.points[(Point.PEAK,i)].latency)
        data.append('%.2f' % waveform.points[(Point.PEAK,i)].amplitude)
        data.append('%.2f' % waveform.points[(Point.VALLEY,i)].latency)
        data.append('%.2f' % waveform.points[(Point.VALLEY,i)].amplitude)
    return '\t'.join(data)

def filter_string(waveform):
    header = 'Filter history (zpk format):'
    if waveform._zpk is None:
        return header + ' No filtering'
    else:
        templ = 'Pass %d -- z: %r, p: %r, k: %r'
        filt = [templ % (i,z,p,k) for i,(z,p,k) in enumerate(waveform._zpk)]
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
        filestring = time.strftime('%Y-%m-%d-%H-%M-%S-',
                time.gmtime(filetime))
        new_fname = os.path.join(base, filestring+fname)
        os.rename(file, new_fname) 
    return open(file, 'w')

