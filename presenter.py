# vim: set fileencoding=utf-8

import wx
from abrpanel import WaveformPlot
from peakdetect import find_np, iterator_np
from datatype import WaveformPoint
from numpy import concatenate
from numpy import array
import operator
from matplotlib.transforms import blended_transform_factory

import filter_HDF5_file as peakio


class WaveformPresenter(object):

    def __init__(self, model, view, interactor, options=None):
        self._toggle = {}
        self._iterator = {}
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

        n = len(self.model.waveforms)
        offset_delta = 0.8/n
        offset = 0.05
        self.plots = []

        bounds = []
        text_trans = blended_transform_factory(self.view.figure.transFigure,
                                               self.view.subplot.transAxes)
        for waveform in self.model.waveforms:
            plot = WaveformPlot(waveform, self.view.subplot, offset)
            bounds.append(abs(waveform.y.min()))
            bounds.append(abs(waveform.y.max()))
            self.plots.append(plot)
            text = self.view.figure.text(0.02, offset, str(waveform.level))

            # For some reason if we try to set a transform in the call to
            # figure.text, it does not get set, so we set it after the text
            # object has been created.
            text.set_transform(text_trans)
            offset += offset_delta

        self.view.subplot.set_autoscale_on(False)
        self.view.subplot.axis(xmax=8.5, ymin=0)
        self.view.subplot.set_yticks([])

        self.current = len(self.model.waveforms)-1
        self.update_labels()
        self._reg_scale = sum(bounds)/2
        self._norm_scale = 1*n
        self.scale = self._reg_scale

    def delete(self):
        self.plots[self.current].remove()
        del self.plots[self.current]
        del self.model.waveforms[self.current]
        self._plotupdate = True

    def save(self):
        if self.P and self.N:
            msg = peakio.save(self.model)
            self.view.GetTopLevelParent().SetStatusText(msg)
        else:
            msg = "Please identify N1-5 before saving"
            wx.MessageBox(msg, "Error")

    def update(self):
        if self._plotupdate:
            self._plotupdate = False
            self._redrawflag = True
            for p in self.plots:
                p.update()
        if self._redrawflag:
            self._redrawflag = False
            self.view.canvas.draw()

    def get_current(self):
        try:
            return self._current
        except AttributeError:
            return -1

    def set_current(self, value):
        if value < 0 or value > len(self.model.waveforms)-1:
            pass
        elif value == self.current:
            pass
        else:
            self.iterator = None
            try:
                self.plots[self.current].current = False
            except IndexError:
                pass
            self.plots[value].current = True
            self._redrawflag = True
            self._current = value

    current = property(get_current, set_current, None, None)

    def get_scale(self):
        try:
            return self._scale
        except AttributeError:
            return 10

    def set_scale(self, value):
        if value < 0:
            return
        self._scale = value
        self.view.subplot.axis(ymin=0, ymax=value)
        self.update_labels()
        self._redrawflag = True

    scale = property(get_scale, set_scale, None, None)

    def update_labels(self):
        if self.normalized:
            self.view.set_title('normalized')
        else:
            self.view.set_title('raw')

    def get_normalized(self):
        try:
            return self._normalized
        except AttributeError:
            return False

    def set_normalized(self, value):
        if value == self.normalized:
            pass
        else:
            self._normalized = value
            if self._normalized:
                self._reg_scale = self.scale
                self.scale = self._norm_scale
            else:
                self._norm_scale = self.scale
                self.scale = self._reg_scale

            for p in self.plots:
                p.normalized = value
                p.update()
            self._plotupdate = True
            self.update_labels()

    normalized = property(get_normalized, set_normalized)

    def set_threshold(self):
        self.model.threshold = self.model.waveforms[self.current].level
        self._plotupdate = True

    def get_toggle(self):
        try:
            return self._toggle[self.current]
        except AttributeError:
            self._toggle = {}
        except KeyError:
            return None

    def set_toggle(self, value):
        if value == self.toggle:
            pass
        else:
            self.iterator = None
            self.plots[self.current].toggle = value
            self._toggle[self.current] = value
            self._redrawflag = True

    toggle = property(get_toggle, set_toggle, None, None)

    def guess_p(self, start=None):
        self.P = True
        if start is None:
            start = len(self.model.waveforms)
        for i in reversed(range(start)):
            cur = self.model.waveforms[i]
            try:
                prev = self.model.waveforms[i+1]
                i_peaks = self.getindices(prev, WaveformPoint.PEAK)
                a_peaks = prev.y[i_peaks]
                seeds = zip(i_peaks, a_peaks)
                p_indices = find_np(cur.fs, cur.y, guess_algorithm='seed',
                                    guess_algorithm_kw={'seeds': seeds},
                                    nzc_algorithm='noise', n=5)
            except IndexError:
                p_indices = find_np(cur.fs, cur.y, n=5)
            for i, v in enumerate(p_indices):
                self.setpoint(cur, (WaveformPoint.PEAK, i+1), v)

    def update_point(self):
        for i in reversed(range(self.current)):
            cur = self.model.waveforms[i]
            index = self.model.waveforms[i+1].points[self.toggle].index
            amplitude = self.model.waveforms[i+1].y[index]
            seeds = [(index, amplitude)]
            if self.toggle[0] == WaveformPoint.PEAK:
                index, = find_np(cur.fs, cur.y, guess_algorithm="seed", n=1,
                                 guess_algorithm_kw={'seeds': seeds},
                                 nzc_algorithm='noise')
            else:
                index, = find_np(cur.fs, -cur.y, guess_algorithm="seed", n=1,
                                 guess_algorithm_kw={'seeds': seeds},
                                 nzc_algorithm='noise')
            self.setpoint(cur, self.toggle, index)
        self._plotupdate = True

    def guess_n(self, start=None):
        self.N = True
        if start is None:
            start = len(self.model.waveforms)
        for i in reversed(range(start)):
            cur = self.model.waveforms[i]
            p_indices = self.getindices(cur, WaveformPoint.PEAK)
            bounds = concatenate((p_indices, array([len(cur.y)-1])))
            try:
                prev = self.model.waveforms[i+1]
                i_valleys = self.getindices(prev, WaveformPoint.VALLEY)
                a_valleys = prev.y[i_valleys]
                seeds = zip(i_valleys, a_valleys)
                n_indices = find_np(cur.fs, -cur.y, guess_algorithm='seed',
                                    guess_algorithm_kw={'seeds': seeds},
                                    bounds=bounds, nzc_algorithm='noise',
                                    nzc_algorithm_kw={'dev': 0.5})
            except IndexError:
                n_indices = find_np(cur.fs, -cur.y, bounds=bounds,
                                    guess_algorithm='y_fun',
                                    nzc_algorithm='noise',
                                    nzc_algorithm_kw={'dev': 0.5})
            for i, v in enumerate(n_indices):
                self.setpoint(cur, (WaveformPoint.VALLEY, i+1), v)
        self._plotupdate = True

    def setpoint(self, waveform, point, index):
        try:
            waveform.points[point].index = index
        except KeyError:
            waveform.points[point] = WaveformPoint(waveform, index, point)
        self._redrawflag = True

    def getindices(self, waveform, point):
        points = [v for v in waveform.points.values() if v.point_type == point]
        points.sort(key=operator.attrgetter('wave_number'))
        return [p.index for p in points]

    def get_iterator(self):
        iterator = self._iterator.get(self.current, None)
        if iterator is not None:
            return iterator

        if self.toggle is not None:
            waveform = self.model.waveforms[self.current]
            start_index = waveform.points[self.toggle].index
            if self.toggle[0] == WaveformPoint.PEAK:
                iterator = iterator_np(waveform.fs, waveform.y, start_index)
            else:
                iterator = iterator_np(waveform.fs, -waveform.y, start_index)
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

    iterator = property(get_iterator, set_iterator)

    def move_selected_point(self, step):
        if self.toggle is None:
            # No point is currently selected.  Ignore the request
            return

        waveform = self.model.waveforms[self.current]
        waveform.points[self.toggle].index = self.iterator.send(step)
        self.plots[self.current].points[self.toggle].update()
        self._redrawflag = True
