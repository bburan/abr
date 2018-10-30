"""
Collection of classes for handling common data types
"""
from enum import Enum
import functools
import operator

import numpy as np
import pandas as pd
from scipy import signal

from .peakdetect import (generate_latencies_bound, generate_latencies_skewnorm,
                         guess, guess_iter)


@functools.total_ordering
class Point(Enum):

    PEAK = 'peak'
    VALLEY = 'valley'

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplementedError


class ABRWaveform:

    def __init__(self, fs, signal, level):
        self.fs = fs
        self.signal = signal
        self.level = level
        self.points = {}
        self.series = None

    @property
    def x(self):
        return self.signal.index.values

    @property
    def y(self):
        return self.signal.values

    def is_subthreshold(self):
        if self.series.threshold is None:
            return False
        return self.level < self.series.threshold

    def is_suprathreshold(self):
        if self.series.threshold is None:
            return True
        return self.level >= self.series.threshold

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

    def set_point(self, wave, ptype, index):
        if (wave, ptype) not in self.points:
            point = WaveformPoint(self, 0, wave, ptype)
            self.points[wave, ptype] = point
        self.points[wave, ptype].index = int(index)


class WaveformPoint(object):
    '''
    Parameters
    ----------
    TODO
    '''
    def __init__(self, parent, index, wave, ptype):
        self.parent = parent
        self.index = index
        self.point_type = ptype
        self.wave_number = wave

    @property
    def x(self):
        return self.parent.x[self.index]

    @property
    def y(self):
        return self.parent.y[self.index]

    def is_peak(self):
        return self.point_type == Point.PEAK

    def is_valley(self):
        return self.point_type == Point.VALLEY

    @property
    def latency(self):
        if self.parent.is_subthreshold():
            return -np.abs(self.x)
        else:
            return self.x

    @property
    def amplitude(self):
        return self.y


class ABRSeries(object):

    def __init__(self, waveforms, freq=None, threshold=np.nan):
        waveforms.sort(key=operator.attrgetter('level'))
        self.waveforms = waveforms
        self.freq = freq
        self.threshold = threshold
        for waveform in self.waveforms:
            waveform.series = self

    def get_level(self, level):
        for waveform in self.waveforms:
            if waveform.level == level:
                return waveform
        raise AttributeError(f'{level} dB SPL not in series')

    def guess_p(self):
        level_guesses = guess_iter(self.waveforms)
        self._set_points(level_guesses, Point.PEAK)

    def guess_n(self):
        n_latencies = {}
        for w in self.waveforms:
            g = {p.wave_number: p.x for p in w.points.values() if p.is_peak()}
            g = pd.DataFrame({'x': g})
            n_latencies[w.level] = generate_latencies_bound(g)
        level_guesses = guess(self.waveforms, n_latencies, invert=True)
        self._set_points(level_guesses, Point.VALLEY)

    def update_guess(self, level, point):
        waveform = self.get_level(level)
        p = waveform.points[point]
        g = {p.wave_number: p.x}
        g = pd.DataFrame({'x': g})
        latencies = generate_latencies_skewnorm(g)

        i = self.waveforms.index(waveform)
        waveforms = self.waveforms[:i]
        level_guesses = guess_iter(waveforms, latencies, invert=p.is_valley())
        self._set_points(level_guesses, p.point_type)

    def _set_points(self, level_guesses, ptype):
        for level, level_guess in level_guesses.items():
            waveform = self.get_level(level)
            for wave, wave_guess in level_guess.iterrows():
                waveform.set_point(wave, ptype, int(wave_guess['index']))
