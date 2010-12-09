"""
Collection of classes for handling common data types

Created: Sat 23 Jun 2007 12:18:30 PM
Modified: Sat 16 Aug 2008 11:46:13 AM
"""

from __future__ import generators
from __future__ import division

__author__ = 'Brad Buran, bburan@alum.mit.edu'

from signal_additional import filtfilt
from scipy import signal as sig
import numpy as np
from copy import deepcopy

import operator

def Enum(*names):
   ##assert names, "Empty enums are not supported" # <- Don't like empty enums? Uncomment!

   class EnumClass(object):
      __slots__ = names
      def __iter__(self):        return iter(constants)
      def __len__(self):         return len(constants)
      def __getitem__(self, i):  return constants[i]
      def __repr__(self):        return 'Enum' + str(names)
      def __str__(self):         return 'enum ' + str(constants)

   class EnumValue(object):
      __slots__ = ('__value')
      def __init__(self, value): self.__value = value
      Value = property(lambda self: self.__value)
      EnumType = property(lambda self: EnumType)
      def __hash__(self):        return hash(self.__value)
      def __cmp__(self, other):
         # C fans might want to remove the following assertion
         # to make all enums comparable by ordinal value {;))
         assert self.EnumType is other.EnumType, "Only values from the same enum are comparable"
         return cmp(self.__value, other.__value)
      def __invert__(self):      return constants[maximum - self.__value]
      def __nonzero__(self):     return bool(self.__value)
      def __repr__(self):        return str(names[self.__value])

   maximum = len(names) - 1
   constants = [None] * len(names)
   for i, each in enumerate(names):
      val = EnumValue(i)
      setattr(EnumClass, each, val)
      constants[i] = val
   constants = tuple(constants)
   EnumType = EnumClass()
   return EnumType

Th = Enum('SUB', 'TH', 'SUPRA', 'UNK')
Point = Enum('PEAK', 'VALLEY') 

###############################################################################
# Waveforms
###############################################################################
class waveform(object):

    def __init__(self, fs, signal, invert=False, filter=False, 
            normalize=False, zpk=[]):
        self.fs = fs
        #Record of filters that have been applied to waveform
        self._zpk = zpk
        #Time in msec
        self.x = np.arange(len(signal)) * 1000.0 / self.fs
        #Voltage in microvolts
        self.y = signal

        if invert:
            self.invert()
        if filter:
            self.filter()
        if normalize:
            self.normalize()

    def filter(self, N=1, W=(200, 10e3), btype='bandpass', ftype='butterworth',
            method='filtfilt'):

        """Returns waveform filtered using filter paramters specified. If none
        are specified, performs bandpass filtering (1st order butterworth)
        with fl=200Hz and fh=10000Hz.  Note that the default uses filtfilt
        using a 1st order butterworth, which essentially has the same effect
        as a 2nd order with lfilt (but without the phase delay).  
        """
        Wn = np.asarray(W)/self.fs
        kwargs = dict(N=N, Wn=Wn, btype=btype, ftype=ftype)
        b, a = sig.iirfilter(output='ba', **kwargs)
        zpk = sig.iirfilter(output='zpk', **kwargs)

        self._zpk.append(zpk)
        if method == 'filtfilt': self.y = filtfilt(b, a, self.y)
        else: raise NotImplementedError, '%s not supported' % method

    def rectify(self, cutoff=0):
        self.y[self.y<cutoff] = cutoff

    def rectified(self, *args, **kwargs):
        waveform = deepcopy(self)
        waveform.rectify(*args, **kwargs)
        return waveform

    def filtered(self, *args, **kwargs):
        waveform = deepcopy(self)
        waveform.filter(*args, **kwargs)
        return waveform

    def normalize(self):
        '''Returns waveform normalized to one 1(unit) peak to peak
        amplitude.
        ''' 
        amplitude = self.y.max() - self.y.min()
        self.y = self.y / amplitude

    def normalized(self):
        waveform = deepcopy(self)
        waveform.normalize()
        return waveform

    def invert(self):
        self.y = -self.y

    def inverted(self):
        waveform = deepcopy(self)
        waveform.invert()
        return waveform

    def fft(self):
        freq = np.fft.fftfreq(len(self.y), 1/self.fs)
        fourier = np.fft.fft(self.y)
        magnitude = np.abs(fourier)/2**.5
        #magnitude = 20*np.log(magnitude)
        return freq, magnitude

    def freqclip(self, cutoff):
        freq, magnitude = self.fft()
        mask = (freq>cutoff)^(freq<-cutoff)
        magnitude[mask] = 0
        self.y = np.fft.ifft(magnitude)

    def stat(self, bounds, func):
        lb = bounds[0] / ((1/self.fs)*1000)
        ub = bounds[1] / ((1/self.fs)*1000)
        return func(self.y[lb:ub])

    def __add__(self, other):
        if not isinstance(other, waveform):
            raise Exception
        if len(other.y) != len(self.y):
            raise Exception
        if other.fs != self.fs:
            raise Exception

        self.y += other.y
        return self

    def __div__(self, other):
        self.y /= other
        return self

#-------------------------------------------------------------------------------

class waveformpoint(object):

    def __init__(self, parent, index, point):
        self.parent = parent
        self.index = index
        self.point = point

    def get_x(self):
        return self.parent.x[self.index]

    def get_y(self):
        return self.parent.y[self.index]

    x = property(get_x, None, None, None)
    y = property(get_y, None, None, None)

    def get_latency(self):
        if self.parent.threshold in (Th.UNK, Th.SUB):
            return -np.abs(self.x)
        else:
            return self.x

    def get_amplitude(self):
        return self.y

    latency = property(get_latency, None, None, None)
    amplitude = property(get_amplitude, None, None, None)

#-------------------------------------------------------------------------------

class abrwaveform(waveform):
    
    def __init__(self, fs, signal, level, invert=False, filter=False, 
            normalize=False, zpk=[]):
        waveform.__init__(self, fs, signal, invert, filter, normalize, zpk)
        self.level = level
        self.threshold = Th.UNK

#-------------------------------------------------------------------------------

class series(object):
    
    pass

class sortedseries(series):
    """Container for a group of objects that vary along a single parametric axis 
    (such as level or frequency).  The objects are sorted via __cmp__
    """

    def __init__(self, series, key=None):
        series.sort(key=key)
        self.series = series

#-------------------------------------------------------------------------------

class abrseries(sortedseries):

    def __init__(self, waveforms, freq=None, threshold=None):
        sortedseries.__init__(self, waveforms, operator.attrgetter('level'))
        self.freq = freq
        if threshold is None:
            for w in self.series: w.threshold = Th.UNK
        else:
            self.threshold = threshold

    def set_threshold(self, threshold):
        if not self.threshold == threshold:
            self.__threshold = threshold
            for w in self.series:
                if w.level > threshold:
                    w.threshold = Th.SUPRA
                elif w.level == threshold:
                    w.threshold = Th.TH
                else:
                    w.threshold = Th.SUB

    def get_threshold(self):
        try: return self.__threshold
        except AttributeError: return None

    threshold = property(get_threshold, set_threshold, None, None)

    def get(self, level):
        for w in self.series:
            if w.level == level: return w
        return None
