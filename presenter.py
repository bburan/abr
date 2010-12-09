#!/usr/bin/env python
# vim: set fileencoding=utf-8

"""
Created: Sat 23 Jun 2007 12:18:30 PM
Modified: Wed 13 Feb 2008 02:47:16 PM
"""

import wx
from abrpanel import WaveformPlot
from peakdetect import find_np
from peakdetect import manual_np
from datatype import Point
from datatype import waveformpoint
from numpy import concatenate
from numpy import array
import operator

import filter_EPL_LabVIEW_ABRIO_File as peakio
import wx.lib.pubsub as pubsub

#----------------------------------------------------------------------------

class WaveformPresenter(object):

    defaultscale = 7
    minscale = 1
    maxscale = 15

    def __init__(self, model, view, interactor, options=None):
        self._redrawflag = True
        self._plotupdate = True
        self.view = view
        self.plots = []
        self.N = False
        self.P = False
        interactor.Install(self, view)
        if model is not None:
            self.load(model, options)

    def load(self, model, options=None):
        self.options = options
        self.model = model
        if self.model.threshold is None:
            self.guess_p()
            if self.options is not None and self.options.nauto:
                self.guess_n()
        else:
            self.N = True
            self.P = True
        self.plots = [WaveformPlot(w, self.view.subplot) \
                for w in self.model.series]
        self.view.subplot.axis(xmax=8.5)
        self.current = len(self.model.series)-1
        self.update_labels()

    def delete(self):
        self.plots[self.current].remove()
        del self.plots[self.current]
        del self.model.series[self.current]
        self._plotupdate = True
        self.view.subplot.axis

    def save(self):
        if self.P and self.N:
            msg = peakio.save(self.model)
            self.view.GetTopLevelParent().SetStatusText(msg)
            pubsub.Publisher().sendMessage("DATA SAVED")
        else:
            msg = "Please identify N1-5 before saving"
            wx.MessageBox(msg, "Error")

    def update(self):
        if self._plotupdate:
            self._plotupdate = False
            self._redrawflag = True
            for p in self.plots:
                p.update()
            #waveform = self.model.series[-1]
            #ymax = (((waveform.y.max()*self.scale + waveform.level)/5)+1)*5
            #self.view.subplot.axis(ymin=0, ymax=ymax, xmax=8.5)
            self.view.subplot.axis(xmax=8.5)
        if self._redrawflag:
            self._redrawflag = False
            self.view.canvas.draw()

    def get_current(self):
        try: return self._current
        except AttributeError: return -1

    def set_current(self, value):
        if value < 0 or value > len(self.model.series)-1: pass
        elif value == self.current: pass
        else:    
            self.iterator = None
            try: self.plots[self.current].current = False
            except IndexError: pass
            self.plots[value].current = True
            self._redrawflag = True
            self._current = value

    current = property(get_current, set_current, None, None)      

    def get_scale(self):
        try: return self._scale
        except AttributeError: return WaveformPresenter.defaultscale

    def set_scale(self, value):
        if value <= WaveformPresenter.minscale: pass
        elif value >= WaveformPresenter.maxscale: pass
        elif value == self.scale: pass
        else:
            self._scale = value
            for p in self.plots:
                p.scale = value
            self.view.set_ylabel(value)    
            self.update_labels()    
            self._redrawflag = True

    scale = property(get_scale, set_scale, None, None)      

    def update_labels(self):
        label = u'\u039CV*%d + dB SPL' % self.scale
        if self.normalized:
            self.view.set_ylabel('normalized ' + label)
        else:
            self.view.set_ylabel(label)

    def get_normalized(self):
        try: return self._normalized
        except AttributeError: return False

    def set_normalized(self, value):
        if value == self.normalized: pass
        else:    
            for p in self.plots:
                p.normalized = value
            self._normalized = value
            self.update_labels()    
            self._plotupdate = True

    normalized = property(get_normalized, set_normalized, None, None)      

    def set_threshold(self):
        self.model.threshold = self.model.series[self.current].level
        self._plotupdate = True

    def get_toggle(self):
        try: return self._toggle[self.current]
        except AttributeError: 
            self._toggle = {}
        except KeyError:    
            pass
        return None

    def set_toggle(self, value):
        if value == self.toggle: pass
        else:
            self.iterator = None
            self.plots[self.current].toggle = value
            self._toggle[self.current] = value
            self._redrawflag = True
        
    toggle = property(get_toggle, set_toggle, None, None)

    def guess_p(self, start=None):
        self.P = True
        if start is None:
            start = len(self.model.series)
        for i in reversed(range(start)):
            cur = self.model.series[i]
            try:
                prev = self.model.series[i+1]
                i_peaks = self.getindices(prev, Point.PEAK)
                a_peaks = prev.y[i_peaks]
                p_indices = find_np(cur.fs, cur.y, algorithm='seed',
                        seeds=zip(i_peaks, a_peaks), nzc='noise_filtered') 
            except IndexError, e:
                p_indices = find_np(cur.fs, cur.y)
            for i,v in enumerate(p_indices):
                self.setpoint(cur, (Point.PEAK, i+1), v)

    def update_point(self):
        for i in reversed(range(self.current)):
            cur = self.model.series[i]
            index = self.model.series[i+1].points[self.toggle].index
            amplitude = self.model.series[i+1].y[index]
            if self.toggle[0] == Point.PEAK:
                index = find_np(cur.fs, cur.y, algorithm="seed", n=1,
                        seeds=[(index, amplitude)], nzc='noise_filtered')[0]
            else:    
                index = find_np(cur.fs, -cur.y, algorithm="seed", n=1,
                        seeds=[(index, amplitude)], nzc='noise_filtered')[0]
            self.setpoint(cur, self.toggle, index)
        self._plotupdate = True

    def guess_n(self, start=None):
        self.N = True
        if start is None:
            start = len(self.model.series)
        for i in reversed(range(start)):
            cur = self.model.series[i]
            p_indices = self.getindices(cur, Point.PEAK)
            bounds = concatenate((p_indices, array([len(cur.y)-1])))
            try:
                prev = self.model.series[i+1]
                i_valleys = self.getindices(prev, Point.VALLEY)
                a_valleys = prev.y[i_valleys]
                n_indices = find_np(cur.fs, -cur.y, algorithm='bound',
                        seeds=zip(i_valleys, a_valleys), bounds=bounds,
                        bounded_algorithm='seed', dev=0.5) 
            except IndexError, e:
                n_indices = find_np(cur.fs, -cur.y, bounds=bounds,
                        algorithm='bound', bounded_algorithm='y_fun', dev=0.5)
            for i,v in enumerate(n_indices):
                self.setpoint(cur, (Point.VALLEY, i+1), v)
        self._plotupdate = True

    def setpoint(self, waveform, point, index):
        if not hasattr(waveform, 'points'):
            setattr(waveform, 'points', {})
        try:
            waveform.points[point].index = index
        except KeyError:
            waveform.points[point] = waveformpoint(waveform, index, point)
        self._redrawflag = True

    def getindices(self, waveform, point):
        points = [(v.point[1], v.index) for v in \
                waveform.points.itervalues() if v.point[0] == point]
        points.sort(key=operator.itemgetter(0))
        return [p for i,p in points]

    def get_iterator(self):
        try:
            if self._iterator[self.current] is not None:
                return self._iterator[self.current]
        except AttributeError:
            self._iterator = {}
        except KeyError:
            pass
        if self.toggle is not None:
            waveform = self.model.series[self.current]
            start_index = waveform.points[self.toggle].index
            if self.toggle[0] == Point.PEAK:
                iterator = manual_np(waveform.fs, waveform.y, start_index)
            else:    
                iterator = manual_np(waveform.fs, -waveform.y, start_index)
            iterator.next()
            self._iterator[self.current] = iterator
            return self._iterator[self.current]    
        else:
            return None

    def set_iterator(self, value):
        try:
            self._iterator[self.current] = value
        except AttributeError:
            self._iterator = {}
            self._iterator[self.current] = value

    iterator = property(get_iterator, set_iterator, None, None)

    def move(self, step):
        if self.toggle is None:
            return
        else:
            waveform = self.model.series[self.current]
            waveform.points[self.toggle].index = self.iterator.send(step)
            self.plots[self.current].points[self.toggle].update()
            self._redrawflag = True

