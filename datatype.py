"""
Collection of classes for handling common data types

Created: Sat 23 Jun 2007 12:18:30 PM
Modified: Sat 16 Aug 2008 11:46:13 AM
"""

from __future__ import division

__author__ = 'Brad Buran, bburan@alum.mit.edu'

from scipy import signal
import numpy as np
from copy import deepcopy

import operator

class Waveform(object):

    def __init__(self, fs, signal, invert=False, filter=False):
        self.fs = fs
        #Time in msec
        self.x = np.arange(len(signal)) * 1000.0 / self.fs
        #Voltage in microvolts
        self.y = signal

        if invert:
            self.invert()
        if filter is not None:
            self.filter(**filter)

    def filter(self, order, lowpass, highpass, ftype='butter'):
        """Returns waveform filtered using filter paramters specified. If none
        are specified, performs bandpass filtering (1st order butterworth)
        with fl=200Hz and fh=10000Hz.  Note that the default uses filtfilt
        using a 1st order butterworth, which essentially has the same effect
        as a 2nd order with lfilt (but without the phase delay).  
        """
        Wn = highpass/self.fs, lowpass/self.fs
        kwargs = dict(N=order, Wn=Wn, btype='band', ftype=ftype)
        b, a = signal.iirfilter(output='ba', **kwargs)
        zpk = signal.iirfilter(output='zpk', **kwargs)
        try:
            self._zpk.append(zpk)
        except:
            self._zpk = [zpk]
        self.y = signal.filtfilt(b, a, self.y)

    def filtered(self, *args, **kwargs):
        waveform = deepcopy(self)
        waveform.filter(*args, **kwargs)
        return waveform

    def invert(self):
        self.y = -self.y

    def inverted(self):
        waveform = deepcopy(self)
        waveform.invert()
        return waveform

    def stat(self, bounds, func):
        lb = bounds[0] / ((1/self.fs)*1000)
        ub = bounds[1] / ((1/self.fs)*1000)
        return func(self.y[lb:ub])


#-------------------------------------------------------------------------------

class WaveformPoint(object):
    '''
    Parameters
    ----------
    parent : waveform
        Waveform point is associated with
    index : 
        Index in waveform signal
    point_type :
        Type
    '''

    PEAK = 'PEAK'
    VALLEY = 'VALLEY'

    def __init__(self, parent, index, point):
        self.parent = parent
        self.index = index
        #self.point = point
        self.point_type = point[0]
        self.wave_number = point[1]

    def _get_x(self):
        return self.parent.x[self.index]

    def _get_y(self):
        return self.parent.y[self.index]

    x = property(_get_x)
    y = property(_get_y)

    def is_peak(self):
        return self.point_type == self.PEAK

    def is_valley(self):
        return self.point_type == self.VALLEY

    def _get_latency(self):
        if self.parent.is_subthreshold():
            return -np.abs(self.x)
        else:
            return self.x

    def _get_amplitude(self):
        return self.y

    latency = property(_get_latency)
    amplitude = property(_get_amplitude)

#-------------------------------------------------------------------------------

class ABRWaveform(Waveform):
    
    def __init__(self, fs, signal, level, series=None, invert=False,
                 filter=False):
        super(ABRWaveform, self).__init__(fs, signal, invert, filter)
        self.level = level
        self.series = series
        self.points = {}

    def is_subthreshold(self):
        return self.level < self.series.threshold

    def is_suprathreshold(self):
        return self.level >= self.series.threshold

#-------------------------------------------------------------------------------

class ABRSeries(object):

    def __init__(self, waveforms, freq=None, threshold=None):
        waveforms.sort(key=operator.attrgetter('level'))
        self.waveforms = waveforms
        self.freq = freq
        self.threshold = threshold
        for waveform in self.waveforms:
            waveform.series = self

    def get(self, level):
        for w in self.waveforms:
            if w.level == level: 
                return w
        return None
