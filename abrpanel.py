#!/usr/bin/env python
# vim: set fileencoding=utf-8

#from datatype import Th
from datatype import WaveformPoint
import wx
import os
from numpy import array
from matplotlib import transforms

#----------------------------------------------------------------------------

class StylePlot(object):

    HIDDEN = { 'alpha': 0 }

    def update(self):
        self.update_plot()
        self.update_style()

    def update_style(self):
        self._setstyle(self.plot, self._getstyle())

    def _setstyle(self, plot, style):
        if type(plot) == type([]):
            for p in plot:
                for k, v in style.iteritems():
                    getattr(p, 'set_' + k)(v)
        else:
            for k, v in style.iteritems():
                getattr(plot, 'set_' + k)(v)

    def _get_current(self):
        try: return self._current
        except AttributeError: return False

    def _set_current(self, flag):
        if self.current is not flag:
            self._current = flag
            self.update()

    current = property(_get_current, _set_current)

    #Method stubs
    def _getstyle(self):
        raise NotImplementedError

    def update_plot(self):
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

    COLORS      = [(1,0,0), (1,1,0), (0,1,0), (0,1,1), (0,0,1)]
    DARK_COLORS = [(.3,0,0), (.3,.3,0), (0,.3,0), (0,.3,.3), (0,0,.3)]

    def __init__(self, parent, figure, point):
        self.figure = figure
        self.parent = parent
        self.point = point
        self.plot, = self.figure.plot(0, 0)
        self.update()

    def remove(self):
        self.figure.lines.remove(self.plot)

    def _getstyle(self):
        # Hide subthreshold points
        if self.parent.waveform.is_subthreshold():
            return self.HIDDEN
        if self.current and self.parent.current:
            return self.TOGGLE

        if self.point.is_peak():
            style = self.PEAK
        else:
            style = self.VALLEY
        index = self.point.wave_number-1
        style['c'] = self.COLORS[index]
        style['markerfacecolor'] = self.COLORS[index]
        return style

    def update_plot(self):
        self.plot.set_data(self.point.x, self.point.y)
        self.plot.set_transform(self.parent.plot.get_transform())

#----------------------------------------------------------------------------

class WaveformPlot(StylePlot):

    CUR_PLOT = {
            'c':            (0,0,0),
            'linewidth':    4,
            'linestyle':    '-',
            'zorder'   :    20,
        }
    PLOT = {
            'c':            (0.6,0.6,0.6),
            'linewidth':    2,
            'linestyle':    '-',
            'zorder'   :    10,
        }
    CUR_SUBTH_PLOT = {
            'c':            (0.3,0.3,0.3),
            'linewidth':    4,
            'linestyle':    ':',
            'zorder'   :    10,
        }
    SUBTH_PLOT = {
            'c':            (0.3,0.3,0.3),
            'linewidth':    2,
            'linestyle':    ':',
            'zorder'   :    10,
        }

    def __init__(self, waveform, axis, offset):
        self.offset = offset
        self.axis = axis
        self.waveform = waveform
        self.normalized = False
        self.current = False
        self.points = {}

        # Compute offset transform
        offset = transforms.Affine2D().translate(0, self.offset)
        self.t_reg = self.axis.transLimits + offset + self.axis.transAxes

        # Compute normalized transform.  Basically the min/max of the waveform
        # are scaled to the range [0, 1] (i.e. normalized) before being passed
        # to the t_reg transform.
        boxin  = transforms.Bbox([[0, self.waveform.y.min()],
                                 [ 1, self.waveform.y.max()]])
        boxout = transforms.Bbox([[0, 0], [1, 1]])
        self.t_norm = transforms.BboxTransform(boxin, boxout) + self.t_reg

        # Create the plot
        self.plot, = self.axis.plot(self.waveform.x, self.waveform.y)
        self.update()

    def __del__(self):
        self.axis.lines.remove(self.plot)
        
    def remove(self):
        self.axis.lines.remove(self.plot)
        for v in self.points.values():
            v.remove()

    STYLE = {
        (True,  True )    : CUR_PLOT,
        (True,  False)    : CUR_SUBTH_PLOT,
        (False, True )    : PLOT,
        (False, False)    : SUBTH_PLOT,
    }

    def _getstyle(self):
        style = self.current, self.waveform.is_suprathreshold()
        return self.STYLE[style]

    def set_toggle(self, point):
        if point is not None:
            if self.toggle is not None:
                self.points[self._toggle].current = False
            self.points[point].current = True
            self._toggle = point

    def get_toggle(self):
        try: 
            return self._toggle
        except AttributeError: 
            return None

    toggle = property(get_toggle, set_toggle)

    def update_data(self):
        self.plot.set_data(self.waveform.x, self.waveform.y)

    def update_plot(self):
        if self.normalized:
            self.plot.set_transform(self.t_norm)
        else:
            self.plot.set_transform(self.t_reg)

    def update(self):
        self.update_plot()
        self.update_style()
        # Check to see if new points were added (e.g. valleys)
        for point, data in self.waveform.points.items():
            if point not in self.points:
                self.points[point] = PointPlot(self, self.axis, data)
        for p in self.points.values():
            p.update()
