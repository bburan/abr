'''
This module defines the import/export routines for interacting with the data
store.  If you wish to customize this, simply define load(), save(), list()
and sort() in this module.

list(location, skip_processed) -- Accepts a location string (provided by the
-d flag or the user options dialog).  In the example below, the location
string is expected to be a directory, but possible variations include a
database connection string.  Skip_Processed is a boolean that indicates
whether or not already processed runs should be skipped.  This function should
return a list of tuples where the tuple is in the format (name, run_location).
Name is the string displayed to the user, while run_location is can be any
Python object that provides the information needed by load() to access the
data from that run.

load(run_location, invert, filter) -- When the program needs a run loaded, it will
pass the run_location provided by list().  Invert is a boolean flag indicating
whether waveform polarity should be flipped.  Filter is a dictionary
containing the following keys:
    1. ftype: any of None, butterworth, bessel, etc.
    2. fh: highpass cutoff (integer in Hz)
    3. fl: lowpass cutoff (integer in Hz)
All objects of the epl.datatype.Waveform class will accept the filter
dictionary and perform the appropriate filtering.  It is recommended you use
the filtering provided by the Waveform class as the history of the filter will
also be recorded.  This function must return an object of the
epl.datatype.ABRSeries class.  See this class for appropriate documentation.

Saves the analyzed data.  Model is of the ABRSeries class and contains
the following attributes:
  1. filename: name of the file that the data was originally loaded from
  2. freq: stimulus frequency
  3. waveforms: a list of waveforms (in the ABRWaveform class format) that
  belong to the series. 

The ABRWaveform class contains the following attributes:
  1. level: stimulus level
  2. zpk: a list containing the history of filtering for the waveform,
  stored as zpk format.  [0] is the earliest filtering, [-1] is the most
  recent.  
  3. points: a dictionary containing the points P1-5 and N1-5.  Each point
  is an object with amplitude and latency attributes.

The save function must return a message.  If there is an error in saving,
throw the appropriate exception.
'''

import epl
from epl import db, fileio as io
from epl.datatype import abrwaveform, abrseries, Point
import pyodbc
import numpy as np

load_query = '''
SELECT sampling_frequency, waveform_path, stimulus_level, 
    inverted_polarity, stimulus_frequency
FROM abr_freq_level as l inner join abr_freq as f
    on l.user=f.user and l.animal=f.animal and l.ear=f.ear and l.run=f.run
WHERE
    l.user='%s' and l.animal=%d and l.ear='%s' and l.run=%d
ORDER BY stimulus_level
'''

load_th_query = '''
SELECT th
FROM abr_freq
WHERE user='%s' and animal=%d and ear='%s' and run=%d
'''

load_peak_query = '''
SELECT amplitude, latency, peak_type, peak_num, stimulus_level
FROM abr_freq_level_peak
WHERE user='%s' and animal=%d and ear='%s' and run=%d
ORDER BY stimulus_level, peak_num, peak_type
'''

def load(run, invert=False, filter=None, load_peaks=True):
    try:
        run = tuple(run.split('-'))
        run = (run[0], int(run[1]), run[2], int(run[3]))
    except AttributeError:
        run = run[:-1]
    run = tuple(run)

    data = db.get(load_query % run, format='array')
    if invert:
        waveforms = [io.get(d[1], fs=d[0], level=d[2]).inverted() for d in data]
    else:
        waveforms = [io.get(d[1], fs=d[0], level=d[2]) for d in data]

    if d[3]:
        waveforms = [w.inverted() for w in waveforms]

    if filter is not None and filter['ftype'] != 'None':
        waveforms = [w.filtered(**filter) for w in waveforms]
    ser = abrseries(waveforms, d[-1])
    ser.location = run

    th = db.get(load_th_query % run)[0][0]
    if load_peaks and not np.isnan(th):
        ser.set_threshold(th)
        peak_data = db.get(load_peak_query % run)
        peak_data, levels = epl.util.categorize(peak_data,
                peak_data.stimulus_level) 
        data = zip(levels, peak_data)
        data.sort()
        levels, peak_data = zip(*data)

        for w, data, level in zip(ser.series, peak_data, levels):
            assert level==w.level
            w.points = {}
            for amp, lat, ptype, pnum, level in data:
                type = epl.dt.Point.PEAK if ptype == 'P' else epl.dt.Point.VALLEY
                point = (type, pnum)
                index = round(abs(lat)*100) # fs is 100e3, l is in msec
                w.points[point] = epl.dt.waveformpoint(w, index, point)
                #assert w.points[point].get_amplitude() == amp
                #assert w.points[point].get_latency() == level
        ser.load_peaks = True

    return ser

user_query = """
    SELECT distinct u.user
    FROM user as u inner join abr_freq as f
        ON u.user=f.user
    """

animal_query = """
    SELECT distinct a.user, a.animal
    FROM animal as a inner join abr_freq as f
        ON a.user=f.user and a.animal=f.animal
    WHERE a.user='%s'
    """

animal_query = """
    SELECT distinct f.user, f.animal
    FROM (animal as a inner join noise_exposure as n
        on n.user=a.user and n.animal=a.animal) inner join abr_freq as f
        ON a.user=f.user and a.animal=f.animal

    WHERE a.user='%s' and n.booth='SGK' and n.noise_level=94
    """

ear_query = """
    SELECT distinct e.user, e.animal, e.ear
    FROM ear as e inner join abr_freq as f
        ON e.user=f.user and e.animal=f.animal and e.ear=f.ear
    WHERE e.user='%s' and e.animal=%d
    """
run_query = """
    SELECT user, animal, ear, run, stimulus_frequency*1e-3 as freq, th
    FROM abr_freq
    WHERE user='%s' and animal=%d and ear='%s'
    """

def list(location=None, skip_processed=False):
    if location is None or len(location) == 0:
        data = db.get(user_query, format='array')
        return [{'display':     '%s' % tuple(d),
                'data':         d,
                'sort_key':     tuple(d),
                'has_children': 1,
                'data_string':  '%s' % repr(d),
                } for d in data]
    elif len(location) == 1:
        data = db.get(animal_query % tuple(location), format='array')
        return [{'display':     '%d' % d[-1],
                'data':         d,
                'sort_key':     tuple(d),
                'has_children': 1,
                'data_string':  '%s' % repr(d),
                } for d in data]
    elif len(location) == 2:
        data = db.get(ear_query % tuple(location), format='array')
        return [{'display':     '%s' % d[-1],
                'data':         d,
                'sort_key':     tuple(d),
                'has_children': 1,
                'data_string':  '%s' % repr(d),
                } for d in data]
    elif len(location) == 3:
        data = db.get(run_query % tuple(location), format='array')
        return [{'display':     'Run %d - %.2f kHz' % tuple(d[3:5]),
                'data':         d,
                'sort_key':     tuple(d),
                'has_children': 0,
                'data_string':  '%s-%d-%s-%d' % tuple(d[:-2]),
                'processed':    d[-1] is not None,
                } for d in data]
    elif len(location) == 5:
        return None

listall_query = """
    SELECT f.user, f.animal, f.ear, f.run, stimulus_frequency*1e-3
    FROM ((abr_freq as f inner join animal as a
            ON f.user=a.user and f.animal=a.animal) inner join noise_exposure as
            n on n.user=a.user and n.animal=a.animal)
        LEFT JOIN abr_freq_level_peak as p
        ON f.user=p.user and f.animal=p.animal and f.ear=p.ear and f.run=p.run
    WHERE latency is NULL and f.user='BNB' and a.strain='CBA/CaJ' and
        n.booth='SGK' and n.noise_level=94
    ORDER BY f.user, f.animal, f.ear, stimulus_frequency DESC
    """

def listall(source):
    data = db.get(listall_query, format='array')
    return [{'display':     'Run %d - %.2f kHz' % tuple(d[-2:]),
            'data':         d,
            'sort_key':     tuple(d),
            'has_children': 0,
            'data_string':  '%s-%d-%s-%d' % tuple(d[:-1]),
            } for d in data]

save_peak_query = """
    INSERT INTO abr_freq_level_peak (amplitude, latency, peak_type, peak_num, 
    user, animal, ear, run, stimulus_level) VALUES (%.2f, %.2f, '%s', %d, 
    '%s', %s, '%s', %s, %s)
    """

update_peak_query = """
    UPDATE abr_freq_level_peak 
    SET amplitude=%.2f, latency=%.2f
    WHERE peak_type='%s' and peak_num=%d and user='%s' and animal=%s and 
        ear='%s' and run=%s and stimulus_level=%d
    """

save_th_query = """
    UPDATE abr_freq
    SET th=%d
    WHERE user='%s' and animal=%s and ear='%s' and run=%s
    """

def save(model):
    cn = db.connect()
    cur = cn.cursor()
    th = -10 if model.threshold is None else model.threshold
    cur.execute(save_th_query % ((th,)+model.location))
    for w in model.series:
        for p,v in w.points.items():
            peak_type = 'P' if Point.PEAK == p[0] else 'N'
            data = (v.amplitude, v.latency, peak_type, p[1]) + model.location \
                + (w.level,)
            try:
                cur.execute(save_peak_query % data)
            except pyodbc.IntegrityError:
                cur.execute(update_peak_query % data)
    cn.commit()
    return 'Successfully saved waveform'
