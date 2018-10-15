import numpy as np
import operator

from atom.api import (Atom, Typed, Dict, List, Bool, Int, Float, Tuple,
                      Property, Value)

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib import transforms as T

from abr.abrpanel import WaveformPlot
from abr.datatype import ABRSeries, WaveformPoint
from abr.peakdetect import find_np, iterator_np
from abr.parsers import registry

# Maximum spacing, in seconds, between positive and negative points of wave.
MAX_PN_DELTA = 0.25


def plot_model(axes, model):
    n = len(model.waveforms)
    offset_step = 1/(n+1)
    plots = []

    text_trans = T.blended_transform_factory(axes.figure.transFigure,
                                             axes.transAxes)

    limits = [(w.y.min(), w.y.max()) for w in model.waveforms]
    base_scale = np.mean(np.abs(np.array(limits)))

    bscale_in_box = T.Bbox([[0, -base_scale], [1, base_scale]])
    bscale_in = T.BboxTransformFrom(bscale_in_box)
    bscale_out = T.BboxTransformTo(T.Bbox([[0, -1], [1, 1]]))

    tscale_in_box = T.Bbox([[0, -1], [1, 1]])
    tscale_in = T.BboxTransformFrom(tscale_in_box)
    tscale_out = T.BboxTransformTo(T.Bbox([[0, 0], [1, offset_step]]))

    boxes = {
        'tscale': tscale_in_box,
        'tnorm': [],
        'norm_limits': limits/base_scale,
    }

    for i, waveform in enumerate(model.waveforms):
        y_min, y_max = waveform.y.min(), waveform.y.max()
        tnorm_in_box = T.Bbox([[0, -1], [1, 1]])
        tnorm_in = T.BboxTransformFrom(tnorm_in_box)
        tnorm_out_box = T.Bbox([[0, -1], [1, 1]])
        tnorm_out = T.BboxTransformTo(tnorm_out_box)
        boxes['tnorm'].append(tnorm_in_box)

        offset = offset_step * i + offset_step * 0.5
        translate = T.Affine2D().translate(0, offset)

        y_trans = bscale_in + bscale_out + \
            tnorm_in + tnorm_out + \
            tscale_in + tscale_out + \
            translate + axes.transAxes
        trans = T.blended_transform_factory(axes.transData, y_trans)

        plot = WaveformPlot(waveform, axes, trans)
        plots.append(plot)

        text_trans = T.blended_transform_factory(axes.transAxes, y_trans)
        axes.text(-0.05, 0, f'{waveform.level}', transform=text_trans)

    axes.set_yticks([])
    for spine in ('top', 'left', 'right'):
        axes.spines[spine].set_visible(False)

    return plots, boxes


class WaveformPresenter(Atom):

    figure = Typed(Figure, {})
    axes = Typed(Axes)
    options = Typed(object)
    model = Typed(ABRSeries)

    current = Property()

    toggle = Property()
    scale = Property()
    normalized = Property()
    boxes = Dict()

    iterator = Value()

    _current = Int()
    _toggle = Value()
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
        self._current = 0
        self.axes.clear()
        self.model = model
        self.plots, self.boxes = plot_model(self.axes, self.model)
        self.normalized = False
        self.N = False
        self.P = False

        # Set current before toggle. Ordering is important.
        self.current = len(self.model.waveforms)-1
        self.toggle = None
        self.iterator = None
        if self.figure.canvas is not None:
            self.figure.canvas.draw()

    def save(self):
        if  np.isnan(self.model.threshold):
            raise ValueError('Threshold not set')
        if not self.P or not self.N:
            raise ValueError('Waves not identified')
        msg = registry.save(self.model, self.options)
        self.close()

    def update(self):
        for p in self.plots:
            p.update()
        try:
            self.axes.figure.canvas.draw()
        except:
            pass

    def _get_current(self):
        return self._current

    def _set_current(self, value):
        if not (0 <= value < len(self.model.waveforms)):
            return
        if value == self.current:
            return
        self.plots[self.current].current = False
        self.plots[value].current = True
        self._current = value
        self.update()

    def _get_scale(self):
        return self.boxes['tscale'].ymax

    def _set_scale(self, value):
        if value < 0:
            return
        box = np.array([[0, -value], [1, value]])
        self.boxes['tscale'].set_points(box)
        self.figure.canvas.draw()

    def _get_normalized(self):
        box = self.boxes['tnorm'][0]
        return not ((box.ymin == -1) and (box.ymax == 1))

    def _set_normalized(self, value):
        if value:
            zipped = zip(self.boxes['tnorm'], self.boxes['norm_limits'])
            for box, (lb, ub) in zipped:
                points = np.array([[0, lb], [1, ub]])
                box.set_points(points)
        else:
            for box in self.boxes['tnorm']:
                points = np.array([[0, -1], [1, 1]])
                box.set_points(points)
        label = 'normalized' if value else 'raw'
        self.axes.set_title(label)
        try:
            self.figure.canvas.draw()
        except AttributeError:
            pass

    def set_suprathreshold(self):
        self.model.threshold = -np.inf
        self.update()

    def set_subthreshold(self):
        self.model.threshold = np.inf
        if not self.P:
            self.guess_p()
        if not self.N:
            self.guess_n()
        self.save()
        self.update()

    def set_threshold(self):
        self.model.threshold = self.model.waveforms[self.current].level
        self.update()

    def _get_toggle(self):
        return self._toggle

    def _set_toggle(self, value):
        if value == self.toggle:
            return

        for plot in self.plots:
            point = plot.points.get(self.toggle)
            if point is not None:
                point.current = False

        self._toggle = value
        for plot in self.plots:
            point = plot.points.get(value)
            if point is not None:
                point.current = True

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
        self.iterator = self.get_iterator()
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
        self.iterator = self.get_iterator()
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
