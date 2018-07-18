import numpy as np
import operator

from atom.api import (Atom, Typed, Dict, List, Bool, Int, Float, Tuple,
                      Property, Value)

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.transforms import blended_transform_factory

from abr.abrpanel import WaveformPlot
from abr.datatype import ABRSeries, WaveformPoint
from abr.peakdetect import find_np, iterator_np
from abr.parsers import registry


def plot_model(axes, model):
    n = len(model.waveforms)
    offset_delta = 0.8/n
    offset = 0.05
    plots = []

    bounds = []
    text_trans = blended_transform_factory(axes.figure.transFigure,
                                           axes.transAxes)
    for waveform in model.waveforms:
        plot = WaveformPlot(waveform, axes, offset)
        bounds.append(abs(waveform.y.min()))
        bounds.append(abs(waveform.y.max()))
        plots.append(plot)
        text = axes.text(0.02, offset, str(waveform.level))

        # For some reason if we try to set a transform in the call to
        # figure.text, it does not get set, so we set it after the text
        # object has been created.
        text.set_transform(text_trans)
        offset += offset_delta

    axes.set_autoscale_on(False)

    # Set the view limits (e.g. 0-8.5 msec)
    #self.view.subplot.axis(xmin=0, xmax=8.5, ymin=0)
    axes.set_yticks([])
    return plots, bounds


class WaveformPresenter(Atom):

    figure = Typed(Figure, {})
    axes = Typed(Axes)
    options = Typed(object)
    model = Typed(ABRSeries)

    current = Property()
    toggle = Property()
    scale = Property()
    normalized = Property()

    iterator = Value()

    _normalized = Bool()
    _current = Int()
    _toggle = Value()
    _scale = Float()
    _reg_scale = Float()
    _norm_scale = Float()
    plots = List()
    N = Bool(False)
    P = Bool(False)

    def _default_axes(self):
        axes = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])
        font = {'fontsize': 14, 'fontweight': 'bold'}
        axes.set_xlabel('Time (msec)', font)
        axes.set_ylabel('Amplitude (uV)', font)
        axes.set_yticks([])
        return axes

    def __init__(self, options):
        self.options = options

    def load(self, model):
        self.axes.clear()
        self.model = model
        self.plots, bounds = plot_model(self.axes, self.model)
        self.N = False
        self.P = False
        self.toggle = None
        self.iterator = None
        self.normalized = False
        self.current = len(self.model.waveforms)-1
        self.update_labels()
        self._reg_scale = sum(bounds)/2
        self._norm_scale = 1*len(self.plots)
        self.scale = self._reg_scale
        try:
            self.figure.canvas.draw()
        except:
            pass

    def save(self):
        if  np.isnan(self.model.threshold):
            raise ValueError('Threshold not set')
        if not self.P or not self.N:
            raise ValueError('Waves not identified')
        msg = registry.save(self.model, self.options)
        self.close()

    def update(self):
        self.iterator = self.get_iterator()
        for p in self.plots:
            p.update()
        try:
            self.axes.figure.canvas.draw()
        except:
            pass


    def _get_current(self):
        return self._current

    def _set_current(self, value):
        if value < 0 or value > len(self.model.waveforms)-1:
            return
        if value == self.current:
            return

        try:
            self.plots[self.current].current = False
            self.plots[self.current].toggled = None
        except IndexError:
            pass
        self.plots[value].current = True
        self.plots[value].toggle = self.toggle
        self._current = value
        self.update()

    def _get_scale(self):
        return self._scale

    def _set_scale(self, value):
        if value < 0:
            return
        self._scale = value
        self.axes.axis(ymin=0, ymax=value)
        self.update_labels()
        self.update()

    def update_labels(self):
        label = 'normalized' if self.normalized else 'raw'
        self.axes.set_title(label)

    def _get_normalized(self):
        return self._normalized

    def _set_normalized(self, value):
        if value == self.normalized:
            return

        self._normalized = value
        if self._normalized:
            self._reg_scale, self.scale = self.scale, self._norm_scale
        else:
            self._norm_scale, self.scale = self.scale, self._reg_scale

        for p in self.plots:
            p.normalized = value
            p.update()
        self.update_labels()
        self.update()

    def set_suprathreshold(self):
        self.model.threshold = -np.inf
        self.update()

    def set_subthreshold(self):
        self.model.threshold = np.inf
        self.update()

    def set_threshold(self):
        self.model.threshold = self.model.waveforms[self.current].level
        self.update()

    def _get_toggle(self):
        return self._toggle

    def _set_toggle(self, value):
        if value == self.toggle:
            pass
        else:
            self.plots[self.current].toggle = value
            self._toggle = value
            self.update()

    def guess_p(self, start=None):
        if start is None:
            start = len(self.model.waveforms)
        for i in reversed(range(start)):
            cur = self.model.waveforms[i]
            nzc_algorithm_kw = {'min_latency': cur.min_latency}
            try:
                prev = self.model.waveforms[i+1]
                i_peaks = self.getindices(prev, WaveformPoint.PEAK)
                a_peaks = prev.y[i_peaks]
                seeds = list(zip(i_peaks, a_peaks))
                guess_algorithm_kw = {'seeds': seeds}
                p_indices = find_np(cur.fs, cur.y, guess_algorithm='seed',
                                    nzc_algorithm='noise',
                                    n=self.options.n_waves,
                                    guess_algorithm_kw=guess_algorithm_kw,
                                    nzc_algorithm_kw=nzc_algorithm_kw)
            except IndexError:
                p_indices = find_np(cur.fs, cur.y, n=self.options.n_waves,
                                    nzc_algorithm='temporal',
                                    nzc_algorithm_kw=nzc_algorithm_kw)
            for i, v in enumerate(p_indices):
                self.setpoint(cur, (WaveformPoint.PEAK, i+1), v)
        self.P = True
        self.current = len(self.model.waveforms)-1
        self.toggle = 'PEAK', 1
        self.update()

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
        self.update()

    def guess_n(self, start=None):
        if start is None:
            start = len(self.model.waveforms)
        for i in reversed(range(start)):
            cur = self.model.waveforms[i]
            p_indices = self.getindices(cur, WaveformPoint.PEAK)
            bounds = np.concatenate((p_indices, np.array([len(cur.y)-1])))
            try:
                prev = self.model.waveforms[i+1]
                i_valleys = self.getindices(prev, WaveformPoint.VALLEY)
                a_valleys = prev.y[i_valleys]
                seeds = list(zip(i_valleys, a_valleys))
                n_indices = find_np(cur.fs, -cur.y, guess_algorithm='seed',
                                    guess_algorithm_kw={'seeds': seeds},
                                    bounds=bounds, nzc_algorithm='noise',
                                    nzc_algorithm_kw={'dev': 0.5},
                                    n=self.options.n_waves)
            except IndexError:
                n_indices = find_np(cur.fs, -cur.y, bounds=bounds,
                                    guess_algorithm='y_fun',
                                    nzc_algorithm='noise',
                                    nzc_algorithm_kw={'dev': 0.5},
                                    n=self.options.n_waves)
            for i, v in enumerate(n_indices):
                self.setpoint(cur, (WaveformPoint.VALLEY, i+1), v)
        self.N = True
        self.current = len(self.model.waveforms)-1
        self.toggle = 'VALLEY', 1
        self.update()

    def setpoint(self, waveform, point, index):
        try:
            waveform.points[point].index = index
        except KeyError:
            waveform.points[point] = WaveformPoint(waveform, index, point)
        self.update()

    def getindices(self, waveform, point):
        points = [v for v in waveform.points.values() if v.point_type == point]
        points.sort(key=operator.attrgetter('wave_number'))
        return [p.index for p in points]

    def get_iterator(self):
        if self.toggle is None:
            return
        waveform = self.model.waveforms[self.current]
        start_index = waveform.points[self.toggle].index
        if self.toggle[0] == WaveformPoint.PEAK:
            iterator = iterator_np(waveform.fs, waveform.y, start_index)
        else:
            iterator = iterator_np(waveform.fs, -waveform.y, start_index)
        next(iterator)
        return iterator

    def move_selected_point(self, step):
        # No point is currently selected.  Ignore the request
        if self.toggle is None:
            return

        waveform = self.model.waveforms[self.current]
        waveform.points[self.toggle].index = self.iterator.send(step)
        self.plots[self.current].points[self.toggle].update()
        self.update()


class SerialWaveformPresenter(WaveformPresenter):

    unprocessed = List()
    current_model = Int()

    def __init__(self, unprocessed, options):
        self.unprocessed = unprocessed
        self.options = options
        self.load_next()
        self.current_model = -1

    def onpress(self, event):
        if event.key == 'pagedown':
            self.load_next()
        elif event.key == 'pageup':
            self.load_prior()
        else:
            super().onpress(event)

    def load_prior(self):
        if self.current_model < 0:
            return
        self.current_model -= 1
        filename, frequency = self.unprocessed[self.current_model]
        model = registry.load(filename, self.options,
                              frequencies=[frequency])[0]
        self.load(model)

    def load_next(self):
        if self.current_model > len(self.unprocessed):
            return
        self.current_model += 1
        filename, frequency = self.unprocessed[self.current_model]
        model = registry.load(filename, self.options,
                              frequencies=[frequency])[0]
        self.load(model)

    def close(self):
        self.load_next()
