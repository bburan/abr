#!/usr/bin/env python

from __future__ import with_statement

import re
from numpy import array
from datatype import abrwaveform
from datatype import abrseries

def loadabr(fname, invert=False, filter=False, fdict=None):
    p_level = re.compile(':LEVELS:([0-9;]+)')
    p_fs = re.compile('SAMPLE \(.sec\): ([0-9]+)')
    p_freq = re.compile('FREQ: ([0-9\.]+)')
    time_pattern = '([0-9]{1,2}/[0-9]{1,2}/[0-9]{4}\t' + \
                   '[0-9]{1,2}:[0-9]{1,2}\s[APM]{2})'
    p_time = re.compile(time_pattern)
    abr_window = 8500 #usec
    try:
        with open(fname) as f:
            data = f.read()

            header, data = data.split('DATA')

            levelstring = p_level.search(header).group(1).strip(';').split(';')
            levels = array(levelstring).astype(float)

            sampling_period = float(p_fs.search(header).group(1))
            fs = 1e6/sampling_period
            cutoff = abr_window / sampling_period
            data = array(data.split()).astype(float)
            data = data.reshape(len(data)/len(levels),len(levels)).T
            data = data[:,:cutoff]

            if invert:
                data = -data

            waveforms = [abrwaveform(fs, w, l) for w, l in zip(data, levels)]

            #Checks for a ABR I-O bug that sometimes saves zeroed waveforms
            for w in waveforms[:]:
                if (w.y==0).all():
                    waveforms.remove(w)

            if filter:
                waveforms = [w.filtered(**fdict) for w in waveforms]

            freq = float(p_freq.search(header).group(1))
            series = abrseries(waveforms, freq)
            abrseries.filename = fname

            #Temporary -- add code to convert to actual date/time object
            abrseries.time = p_time.search(header).group(1)
            return series

    except (AttributeError, ValueError):
        msg = 'Could not parse %s.  Most likely not a valid ABR file.' % fname
        raise IOError, msg

def loadabranalysis(fname):
    th_match = re.compile('Threshold \(dB SPL\): ([\w.]+)')
    freq_match = re.compile('Frequency \(kHz\): ([\d.]+)')
    with open(fname) as f:
        text = f.read()
        th = th_match.search(text).group(1)
        if th == 'None': th = None
        else: th = float(th)
        freq = float(freq_match.search(text).group(1))
    data = loadspreadsheet(fname,header=6)
    return (freq, th, data)
