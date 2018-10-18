"""
Collection of classes for handling common data types
"""
from enum import Enum
import functools
import operator

from scipy import signal
import numpy as np


@functools.total_ordering
class Point(Enum):

    PEAK = 'peak'
    VALLEY = 'valley'

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplementedError


class Waveform(object):

    def __init__(self, fs, signal, filter=None, t0=0):
        self.t0 = t0
        self.fs = fs
        # Time in msec
        self.x = np.arange(signal.shape[-1]) * 1000.0 / self.fs + self.t0
        # Voltage in microvolts
        self.signal = signal
        self.y = self.signal.mean(axis=0)

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

    def stat(self, bounds, func):
        tlb = bounds[0]-self.t0
        tub = bounds[1]-self.t0
        lb = int(round(tlb / ((1/self.fs)*1000)))
        ub = int(round(tub / ((1/self.fs)*1000)))
        return func(self.y[lb:ub])

    def mean(self, lb, ub):
        return self.stat((lb, ub), np.mean)

    def std(self, lb, ub):
        return self.stat((lb, ub), np.std)


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


    def __init__(self, parent, index, point):
        self.parent = parent
        self.index = index
        self.point_type = point[1]
        self.wave_number = point[0]

    def _get_x(self):
        return self.parent.x[self.index]

    def _get_y(self):
        return self.parent.y[self.index]

    x = property(_get_x)
    y = property(_get_y)

    def is_peak(self):
        return self.point_type == Point.PEAK

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

    def __init__(self, fs, signal, level, series=None, filter=None,
                 min_latency=None, t0=0):
        super(ABRWaveform, self).__init__(fs, signal, filter, t0)
        self.level = level
        self.series = series
        self.points = {}
        self.min_latency = min_latency

    def is_subthreshold(self):
        if self.series.threshold is None:
            return False
        return self.level < self.series.threshold

    def is_suprathreshold(self):
        if self.series.threshold is None:
            return True
        return self.level >= self.series.threshold


class ABRSeries(object):

    def __init__(self, waveforms, freq=None, threshold=np.nan):
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
