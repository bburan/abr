import threading
import queue

import numpy as np
import pandas as pd

from atom.api import (Atom, Typed, Dict, List, Bool, Int, Float, Tuple,
                      Property, Value, set_default)
from enaml.application import timed_call

from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib import transforms as T

from abr.abrpanel import WaveformPlot
from abr.datatype import ABRSeries, WaveformPoint, Point
from abr.parsers.dataset import Dataset


def plot_model(axes, model):
    n = len(model.waveforms)
    offset_step = 1/(n+1)
    plots = []

    text_trans = T.blended_transform_factory(axes.figure.transFigure,
                                             axes.transAxes)


    limits = [(w.y.min(), w.y.max()) for w in model.waveforms]
    base_scale = np.mean(np.abs(np.array(limits)))

    bscale_in_box = T.Bbox([[0, -base_scale], [1, base_scale]])
    bscale_out_box = T.Bbox([[0, -1], [1, 1]])
    bscale_in = T.BboxTransformFrom(bscale_in_box)
    bscale_out = T.BboxTransformTo(bscale_out_box)

    tscale_in_box = T.Bbox([[0, -1], [1, 1]])
    tscale_out_box = T.Bbox([[0, 0], [1, offset_step]])
    tscale_in = T.BboxTransformFrom(tscale_in_box)
    tscale_out = T.BboxTransformTo(tscale_out_box)

    minmax_in_box = T.Bbox([[0, 0], [1, 1]])
    minmax_out_box = T.Bbox([[0, 0], [1, 1]])
    minmax_in = T.BboxTransformFrom(minmax_in_box)
    minmax_out = T.BboxTransformTo(minmax_out_box)

    boxes = {
        'tscale': tscale_in_box,
        'tnorm': [],
        'norm_limits': limits/base_scale,
        'minmax': minmax_out_box,
    }

    for i, waveform in enumerate(model.waveforms):
        y_min, y_max = waveform.y.min(), waveform.y.max()
        tnorm_in_box = T.Bbox([[0, -1], [1, 1]])
        tnorm_out_box = T.Bbox([[0, -1], [1, 1]])
        tnorm_in = T.BboxTransformFrom(tnorm_in_box)
        tnorm_out = T.BboxTransformTo(tnorm_out_box)
        boxes['tnorm'].append(tnorm_in_box)

        offset = offset_step * i + offset_step * 0.5
        translate = T.Affine2D().translate(0, offset)

        y_trans = bscale_in + bscale_out + \
            tnorm_in + tnorm_out + \
            tscale_in + tscale_out + \
            translate + \
            minmax_in + minmax_out + \
            axes.transAxes
        trans = T.blended_transform_factory(axes.transData, y_trans)

        plot = WaveformPlot(waveform, axes, trans)
        plots.append(plot)

        text_trans = T.blended_transform_factory(axes.transAxes, y_trans)
        axes.text(-0.05, 0, f'{waveform.level}', transform=text_trans)

    axes.set_yticks([])
    axes.grid()
    for spine in ('top', 'left', 'right'):
        axes.spines[spine].set_visible(False)

    return plots, boxes


class WaveformPresenter(Atom):

    figure = Typed(Figure, {})
    analyzed_filenames = List()

    axes = Typed(Axes)
    dataset = Typed(Dataset)
    model = Typed(ABRSeries)

    current = Property()

    toggle = Property()
    scale = Property()
    normalized = Property()
    top = Property()
    bottom = Property()
    boxes = Dict()

    _current = Int()
    _toggle = Value()
    plots = List()

    threshold_marked = Bool(False)
    peaks_marked = Bool(False)
    valleys_marked = Bool(False)

    parser = Value()
    latencies = Dict()

    batch_mode = Bool(False)

    def _default_axes(self):
        axes = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])
        return axes

    def __init__(self, parser, latencies):
        self.parser = parser
        self.latencies = latencies

    def load(self, dataset):
        self.dataset = dataset
        self.analyzed_filenames = dataset.find_analyzed_files()

        self._current = 0
        self.axes.clear()
        self.axes.set_xlabel('Time (msec)')
        self.model = self.parser.load(dataset)
        self.plots, self.boxes = plot_model(self.axes, self.model)

        self.normalized = False
        self.threshold_marked = False
        self.peaks_marked = False
        self.valleys_marked = False

        # Set current before toggle. Ordering is important.
        self.current = len(self.model.waveforms)-1
        self.toggle = None
        self.update()

    def save(self):
        if np.isnan(self.model.threshold):
            raise ValueError('Threshold not set')
        if self.latencies:
            if not self.peaks_marked or not self.valleys_marked:
                raise ValueError('Waves not identified')
        self.parser.save(self.model)
        self.analyzed_filenames = self.dataset.find_analyzed_files()

    def update(self):
        for p in self.plots:
            p.update()
        if self.axes.figure.canvas is not None:
            self.axes.figure.canvas.draw()

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
        self.update()

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
        self.axes.set_title('normalized' if value else 'raw')
        self.update()

    def _get_top(self):
        return self.boxes['minmax'].ymax

    def _set_top(self, value):
        points = np.array([[0, self.bottom], [1, value]])
        self.boxes['minmax'].set_points(points)
        self.update()

    def _get_bottom(self):
        return self.boxes['minmax'].ymin

    def _set_bottom(self, value):
        points = np.array([[0, value], [1, self.top]])
        self.boxes['minmax'].set_points(points)
        self.update()

    def set_suprathreshold(self):
        self.set_threshold(-np.inf)

    def set_subthreshold(self):
        self.set_threshold(np.inf)
        if self.latencies:
            if not self.peaks_marked:
                self.guess()
            if not self.valleys_marked:
                self.guess()

    def set_threshold(self, threshold=None):
        if threshold is None:
            threshold = self.get_current_waveform().level
        self.model.threshold = threshold
        self.threshold_marked = True
        if self.latencies and not self.peaks_marked:
            self.guess()
        self.update()

    def _get_toggle(self):
        return self._toggle

    def _set_toggle(self, value):
        if value == self._toggle:
            return
        for plot in self.plots:
            point = plot.point_plots.get(self.toggle)
            if point is not None:
                point.current = False
        self._toggle = value
        for plot in self.plots:
            point = plot.point_plots.get(value)
            if point is not None:
                point.current = True
        self.update()

    def guess(self):
        if not self.latencies:
            return
        if not self.peaks_marked:
            self.model.guess_p(self.latencies)
            ptype = Point.PEAK
            self.peaks_marked = True
        elif not self.valleys_marked:
            self.model.guess_n()
            ptype = Point.VALLEY
            self.valleys_marked = True
        else:
            return
        self.update()
        self.current = len(self.model.waveforms)-1
        self.toggle = 1, ptype
        self.update()

    def update_point(self):
        level = self.model.waveforms[self.current].level
        self.model.update_guess(level, self.toggle)
        self.update()

    def move_selected_point(self, step):
        point = self.get_current_point()
        point.move(step)
        self.update()

    def set_selected_point(self, time):
        try:
            point = self.get_current_point()
            index = point.time_to_index(time)
            point.move(('set', index))
            self.update()
        except:
            pass

    def toggle_selected_point_unscorable(self):
        try:
            point = self.get_current_point()
            point.unscorable = not point.unscorable
            self.update()
            self.modified = True
        except:
            pass

    def mark_unscorable(self, mode):
        try:
            for waveform in self.model.waveforms:
                if mode == 'all':
                    waveform.points[self.toggle].unscorable = True
                elif mode == 'descending':
                    if waveform.level <= self.get_current_waveform().level:
                        waveform.points[self.toggle].unscorable = True
            self.update()
            self.modified = True
        except:
            pass

    def get_current_waveform(self):
        return self.model.waveforms[self.current]

    def get_current_point(self):
        return self.get_current_waveform().points[self.toggle]

    def clear_points(self):
        self.model.clear_points()
        self.peaks_marked = False
        self.valleys_marked = False
        self.update()

    def clear_peaks(self):
        self.model.clear_peaks()
        self.peaks_marked = False
        self.update()

    def clear_valleys(self):
        self.model.clear_valleys()
        self.valleys_marked = False
        self.update()

    def load_analysis(self, filename):
        self.clear_points()
        self.parser.load_analysis(self.model, filename)
        self.peaks_marked = True
        self.valleys_marked = True
        self.update()

    def remove_analysis(self, filename):
        filename.unlink()
        items = self.analyzed_filenames[:]
        items.remove(filename)
        self.analyzed_filenames = items


def scan_worker(parser, paths, queue, stop):
    for path in paths:
        for ds in parser.find_unprocessed(path):
            queue.put(('append', ds))
            if stop.is_set():
                break
        if stop.is_set():
            break
    queue.put(('complete',))


class SerialWaveformPresenter(WaveformPresenter):

    unprocessed = List()
    n_unprocessed = Int(0)

    current_model = Int(-1)
    batch_mode = set_default(True)

    scan_paths = Value()
    scan_queue = Value()
    scan_stop_event = Value()
    scan_complete = Bool(False)
    scan_thread = Value()

    def __init__(self, parser, latencies, paths):
        super().__init__(parser, latencies)
        self.scan_paths = paths
        self.scan_queue = queue.Queue()
        self.scan_stop_event = threading.Event()
        args = (self.parser, self.scan_paths, self.scan_queue, self.scan_stop_event)
        self.scan_thread = threading.Thread(target=scan_worker, args=args)
        self.scan_thread.start()
        self.unprocessed = []
        timed_call(100, self.scan_poll)

    def scan_poll(self):
        while True:
            try:
                mesg = self.scan_queue.get(block=False)
                if mesg[0] == 'append':
                    self.unprocessed.append(mesg[1])
                elif mesg[0] == 'complete':
                    self.scan_complete = True
            except queue.Empty:
                if not self.scan_complete:
                    timed_call(100, self.scan_poll)
                break
        self.n_unprocessed = len(self.unprocessed)
        if self.current_model < 0:
            self.load_next()

    def scan_stop(self):
        self.scan_stop_event.set()

    def load_model(self):
        fs = self.unprocessed[self.current_model]
        self.load(fs)

    def load_prior(self):
        if self.current_model < 1:
            return
        self.current_model -= 1
        self.load_model()

    def load_next(self):
        if self.current_model >= (len(self.unprocessed) - 1):
            return
        self.current_model += 1
        self.load_model()

    def save(self):
        super().save()
        self.load_next()
