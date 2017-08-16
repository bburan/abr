"""
Collection of classes for handling common data types
"""

from __future__ import division
from copy import deepcopy

from scipy import signal
import numpy as np

import operator


class Waveform(object):

    def __init__(self, fs, signal, invert=False, filter=False):
        self.fs = fs
        # Time in msec
        self.x = np.arange(signal.shape[-1]) * 1000.0 / self.fs
        # Voltage in microvolts
        self.signal = signal
        self.y = self.signal.mean(axis=0)

        if invert:
            self.invert()
        if filter is not None:
            self.filter(**filter)

    def filter(self, order, lowpass, highpass, ftype='butter'):
        """
        Returns waveform filtered using filter paramters specified. Since
        forward and reverse filtering is used to avoid introducing phase delay,
        the filter order is essentially doubled.
        """
        Wn = highpass/self.fs, lowpass/self.fs
        kwargs = dict(N=order, Wn=Wn, btype='band', ftype=ftype)
        b, a = signal.iirfilter(output='ba', **kwargs)
        zpk = signal.iirfilter(output='zpk', **kwargs)
        try:
            self._zpk.append(zpk)
        except:
            self._zpk = [zpk]
        self.signal = signal.filtfilt(b, a, self.signal, axis=-1)
        self.y = self.signal.mean(axis=0)
        self.y = signal.filtfilt(b, a, self.y)

    def invert(self):
        self.y = -self.y

    def stat(self, bounds, func):
        lb = int(bounds[0] / ((1/self.fs)*1000))
        ub = int(bounds[1] / ((1/self.fs)*1000))
        return func(self.y[lb:ub])


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


class ABRWaveform(Waveform):

    def __init__(self, fs, signal, level, series=None, invert=False,
                 filter=False, min_latency=None):
        super(ABRWaveform, self).__init__(fs, signal, invert, filter)
        self.level = level
        self.series = series
        self.points = {}
        self.min_latency = min_latency

    def is_subthreshold(self):
        return self.level < self.series.threshold

    def is_suprathreshold(self):
        return self.level >= self.series.threshold


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
