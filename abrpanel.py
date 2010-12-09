#!/usr/bin/env python
# vim: set fileencoding=utf-8

from __future__ import with_statement

from datafile import loadabr
from datatype import Th
from datatype import Point
import wx
import re
import os
from numpy import concatenate
from numpy import array
from numpy import where
from numpy import arange

#----------------------------------------------------------------------------

class StylePlot(object):

    HIDDEN = {
            'alpha':        0
        }

    def update(self):
        self._plot()
        self._updatestyle()

    def _updatestyle(self):
        self._setstyle(self.plot, self._getstyle())

    def _setstyle(self, plot, style):
        if type(plot) == type([]):
            for p in plot:
                for k, v in style.iteritems():
                    getattr(p, 'set_' + k)(v)
        else:
            for k, v in style.iteritems():
                getattr(plot, 'set_' + k)(v)

    #Generic properties
    def get_current(self):
        try: return self._current
        except AttributeError: return False

    def set_current(self, flag):
        if self.current is not flag:
            self._current = flag
            self.update()

    current = property(get_current, set_current, None, None)

    #Method stubs
    def _getstyle(self):
        raise NotImplementedError

    def _plot(self):
        pass

#----------------------------------------------------------------------------

class PointPlot(StylePlot):
    
    PEAK = {
            'linestyle':        ' ',
            'marker':           'o',
            'zorder':           20,
            'alpha':            1,
            'markersize':       8,
            'markeredgewidth':  1,
            'markeredgecolor':  (0,0,0)
        }

    PEAK_FADED = {
            'linestyle':        ' ',
            'marker':           'o',
            'zorder':           20,
            'alpha':            0.5,
            'markersize':       8,
            'markeredgewidth':  1,
            'markeredgecolor':  (0,0,0)
        }
    
    VALLEY = {
            'linestyle':        ' ',
            'marker':           '^',
            'zorder':           20,
            'alpha':            1,
            'markersize':       9,
            'markeredgewidth':  1,
            'markeredgecolor':  (0,0,0)
        }

    TOGGLE = {
            'linestyle':        ' ',
            'marker':           's',
            'zorder':           100,
            'alpha':            1,
            'markersize':       8,
            'markeredgewidth':  1,
            'markerfacecolor':  (1,1,1),
            'markeredgecolor':  (0,0,0)
        }

    COLORS = [(1,0,0), (1,1,0), (0,1,0), (0,1,1), (0,0,1)]
    DARK_COLORS = [(.3,0,0), (.3,.3,0), (0,.3,0), (0,.3,.3), (0,0,.3)]

    def __init__(self, parent, figure, point):
        self.figure = figure
        self.parent = parent
        self.faded = False
        self.point = point
        self.update()

    def remove(self):
        self.figure.lines.remove(self.plot)

    def _getstyle(self):
        val = self.point.point[1]
        if self.point.index < 0 or self.parent.waveform.threshold == Th.SUB:
            style = StylePlot.HIDDEN
        elif self.current and self.parent.current:
            style = dict(PointPlot.TOGGLE)
        elif self.point.point[0] == Point.PEAK:
            style = dict(PointPlot.PEAK)
            if self.faded:
                style['c'] = PointPlot.DARK_COLORS[val-1]
                style['markerfacecolor'] = PointPlot.DARK_COLORS[val-1]
            else:    
                style['c'] = PointPlot.COLORS[val-1]
                style['markerfacecolor'] = PointPlot.COLORS[val-1]
        else:
            style = dict(PointPlot.VALLEY)
            style['c'] = PointPlot.COLORS[val-1]
            style['markerfacecolor'] = PointPlot.COLORS[val-1]
        return style

    def _plot(self):
        x = array([self.parent.x[self.point.index]])
        y = array([self.parent.y[self.point.index]])
        try: 
            self.plot.set_data(x,y)
        except AttributeError: 
            self.plot = self.figure.plot(x,y)[0]

#----------------------------------------------------------------------------

class WaveformPlot(StylePlot):

    CUR_PLOT = {
            'c':            (0,0,0),
            'linewidth':    4,
            'linestyle':    '-'
        }
    PLOT = {
            'c':            (0.6,0.6,0.6),
            'linewidth':    2,
            'linestyle':    '-',
            'zorder':       10
        }
    CUR_TH_PLOT = {
            'c':            (0,0,0),
            'linewidth':    4,
            'linestyle':    ':'
        }
    TH_PLOT = {
            'c':            (0.6,0.6,0.6),
            'linewidth':    2,
            'linestyle':    ':'
        }
    CUR_SUBTH_PLOT = {
            'c':            (0.3,0.3,0.3),
            'linewidth':    4,
            'linestyle':    ':'
        }
    SUBTH_PLOT = {
            'c':            (0.3,0.3,0.3),
            'linewidth':    2,
            'linestyle':    ':'
        }

    def __init__(self, waveform, figure=None):
        self.figure = figure
        self.waveform = waveform
        self._scale = 5
        self.update()
        self._pointplots()
        self._normalized = False

    def __del__(self):
        print 'deleting self'
        self.figure.lines.remove(self.plot)
        
    def remove(self):
        self.figure.lines.remove(self.plot)
        for v in self.points.values():
            v.remove()

    def _getstyle(self):
        if self.current: 
            if self.waveform.threshold == Th.TH:
                return WaveformPlot.CUR_TH_PLOT
            elif self.waveform.threshold == Th.SUB:
                return WaveformPlot.CUR_SUBTH_PLOT
            else:
                return WaveformPlot.CUR_PLOT
        else:
            if self.waveform.threshold == Th.TH:
                return WaveformPlot.TH_PLOT
            elif self.waveform.threshold == Th.SUB:
                return WaveformPlot.SUBTH_PLOT
            else:
                return WaveformPlot.PLOT

    def set_toggle(self, point):
        if point is not None:
            key = (point[0],point[1])
            if self.toggle is not None:
                self.points[self._toggle].current = False
            self.points[key].current = True
            self._toggle = key

    def get_toggle(self):
        try: return self._toggle
        except AttributeError: return None

    def set_normalized(self, flag):
        if not flag == self._normalized:
            if flag:
                self.y = self.y_nscaled
            else:
                self.y = self.y_scaled
            self._normalized = flag
            self.update()

    def get_normalized(self):
        try: return self._normalized
        except AttributeError: return False

    def set_scale(self, scale):
        self._scale = scale
        self._scale_plot()
        self.update()

    def get_scale(self):
        return self._scale

    toggle = property(get_toggle, set_toggle, None, None)
    normalized = property(get_normalized, set_normalized, None, None)
    scale = property(get_scale, set_scale, None, None)

    def _scale_plot(self):
        self.y_scaled = self.y_base * self.scale + self.waveform.level
        self.y_nscaled = self.y_nbase * self.scale + self.waveform.level
        if self.normalized:
            self.y = self.y_nscaled
        else:
            self.y = self.y_scaled

    def _plot(self):
        try:
            self.plot.set_data(self.x, self.y)
        except AttributeError:
            self.x = self.waveform.x
            self.y_base = self.waveform.y
            self.y_nbase = self.waveform.normalized().y
            self._scale_plot()
            self.plot = self.figure.plot(self.x, self.y)[0]

    def _pointplots(self):
        self.points = {}
        try:
            for p in self.waveform.points.values():
                key = p.point
                self.points[key] = PointPlot(self, self.figure, p)
        except AttributeError:
            pass

    def update(self):
        self._plot()
        self._updatestyle()
        try:
            for k,v in self.waveform.points.items():
                if k not in self.points:
                    self.points[k] = PointPlot(self, self.figure, v)
        except AttributeError:
            pass
        try:
            for p in self.points.values():
                p.update()
        except AttributeError:
            pass

#-------------------------------------------------------------------------------

class ABRPanel(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY):
        wx.Panel.__init__(self, parent)

        self.figure = Figure((9,8),75)
        self.canvas = PhysiologyCanvas(self, -1, self.figure)
        self.subplot = self.figure.add_subplot(111)
        self.subplot.set_xlabel('Time (msec)', ABRPanel.AXIS_LABEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        self.SetSizer(sizer)

    def set_ylabel(self, label):
        self.subplot.set_ylabel(label, ABRPanel.AXIS_LABEL)
