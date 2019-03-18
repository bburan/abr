"""
Collection of classes for handling common data types
"""
from enum import Enum
import functools
import operator

import numpy as np
import pandas as pd
from scipy import signal

from atom.api import Atom, Int, Typed, Value

from .peakdetect import (generate_latencies_bound, generate_latencies_skewnorm,
                         guess, guess_iter, peak_iterator)


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
        return signal.detrend(self.signal.values)

    def is_subthreshold(self):
        if self.series.threshold is None:
            return False
        return self.level < self.series.threshold

    def is_suprathreshold(self):
        if self.series.threshold is None:
            return True
        return self.level >= self.series.threshold

    def stat(self, lb, ub, func):
        return func(self.signal.loc[lb:ub])

    def mean(self, lb, ub):
        return self.stat(lb, ub, np.mean)

    def std(self, lb, ub):
        return self.stat(lb, ub, np.std)

    def set_point(self, wave, ptype, index):
        if (wave, ptype) not in self.points:
            point = WaveformPoint(self, 0, wave, ptype)
            self.points[wave, ptype] = point
        self.points[wave, ptype].index = int(index)

    def clear_points(self):
        self.points = {}

    def clear_peaks(self):
        for wave, ptype in list(self.points):
            if ptype == Point.PEAK:
                del self.points[wave, ptype]

    def clear_valleys(self):
        for wave, ptype in list(self.points):
            if ptype == Point.VALLEY:
                del self.points[wave, ptype]

    def _set_points(self, guesses, ptype):
        for wave, wave_guess in guesses.iterrows():
            index = wave_guess.get('index', np.nan)
            if not np.isfinite(index):
                index = np.searchsorted(self.x , wave_guess['x'])
                index = np.clip(index, 0, len(self.x)-1)
            else:
                index = int(index)
            self.set_point(wave, ptype, index)


class WaveformPoint(Atom):
    '''
    Parameters
    ----------
    TODO
    '''
    parent = Typed(ABRWaveform)
    index = Int()
    wave_number = Int()
    point_type = Typed(Point)
    iterator = Value()

    def __init__(self, parent, index, wave_number, point_type):
        # Order of setting attributes is important here
        self.parent = parent
        self.point_type = point_type
        self.wave_number = wave_number
        invert = self.is_valley()
        iterator = peak_iterator(parent, index, invert=invert)
        next(iterator)
        self.iterator = iterator
        self.index = index

    def _observe_index(self, event):
        if event['type'] == 'update':
            self.iterator.send(('set', event['value']))

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
        latency = self.x
        if self.parent.is_subthreshold():
            return -np.abs(latency)
        return latency

    @property
    def amplitude(self):
        return self.parent.signal.iloc[self.index]

    def move(self, step):
        self.index = self.iterator.send(step)

    def time_to_index(self, time):
        return np.searchsorted(self.parent.x, time)


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

    def guess_p(self, latencies):
        level_guesses = guess_iter(self.waveforms, latencies)
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

    def clear_points(self):
        for waveform in self.waveforms:
            waveform.clear_points()

    def clear_peaks(self):
        for waveform in self.waveforms:
            waveform.clear_peaks()

    def clear_valleys(self):
        for waveform in self.waveforms:
            waveform.clear_valleys()

    def _set_points(self, level_guesses, ptype):
        for level, level_guess in level_guesses.items():
            waveform = self.get_level(level)
            waveform._set_points(level_guess, ptype)
