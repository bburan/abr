import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from atom.api import Bool, Dict, Event, List, observe, Tuple, Typed, Str
import enaml
from enaml.application import deferred_call
from enaml.core.api import d_, Declarative
from enaml.qt.qt_application import QtApplication

with enaml.imports():
    from abr.compare_window import CompareWindow

from abr.presenter import WaveformPresenter


class Compare(Declarative):

    th = Typed(pd.Series)
    waves = Typed(pd.DataFrame)
    data = Typed(pd.DataFrame)

    as_difference = d_(Bool(False))
    jitter = d_(Bool(False))
    axes = Typed(plt.Axes)
    figure = Typed(plt.Figure)
    plot_map = Dict()

    rater_x = d_(Str())
    rater_y = d_(Str())
    selected_feature = d_(Str())
    selected_point = d_(Tuple(), writable=False)

    available_raters = List()
    available_features = List()
    available_subjects = List()

    def __init__(self, parser, directory):
        th, waves = parser.load_analyses(directory)
        ix = [c for c in waves.columns if not (c.endswith('Latency') or c.endswith('Amplitude') or 'msec' in c)]
        waves = waves.set_index(ix)
        ix.remove('Level')
        th = th.set_index(ix)['thresholds'].clip(lower=-20, upper=100)

        features = [c for c in waves.columns if 'msec' not in c.lower()]
        features.sort(key=lambda x: (int(x[1]), x[0] != 'P', x.split(' ')[1]))
        self.available_features = ['Threshold'] + features
        self.available_raters = th.index.unique('analyzer').tolist()

        super().__init__(th=th, waves=waves)
        self.request_update()

    def _observe_selected_feature(self, event):
        if self.selected_feature == 'Threshold':
            self.data = self.th.unstack('analyzer')
        else:
            self.data = self.waves[self.selected_feature].unstack('analyzer')

    def _default_figure(self):
        context = {
            'axes.spines.left': True,
            'ytick.left': True,
            'figure.subplot.left': 0.15,
            'figure.subplot.bottom': 0.1,
            'figure.subplot.top': 0.95,
            'figure.subplot.right': 0.95,
        }
        with plt.rc_context(context):
            figure, self.axes = plt.subplots(1, 1)
        return figure

    def _default_rater_x(self):
        return self.available_raters[0]

    def _default_rater_y(self):
        i = 1 if (len(self.available_raters) > 1) else 0
        return self.available_raters[i]

    def _default_selected_feature(self):
        return self.available_features[0]

    @observe('rater_x', 'rater_y', 'as_difference', 'jitter', 'selected_feature')
    def request_update(self, event=None):
        if event is not None and event['type'] == 'create':
            return
        deferred_call(self._update_plot)

    def _update_plot(self):
        self.axes.clear()
        self.plot_map = {}

        x = self.data.loc[:, self.rater_x].copy()
        y = self.data.loc[:, self.rater_y].copy()

        self.axes.set_xlabel(f'Rater {self.rater_x}')
        if self.as_difference:
            y -= x
            self.axes.set_ylabel(f'Difference between {self.rater_y} and {self.rater_x}')
        else:
            self.axes.set_ylabel(f'Rater {self.rater_y}')

        if self.jitter:
            bound = (x.max() - x.min()) * 0.025
            x += np.random.uniform(-bound, bound, len(x))
            y += np.random.uniform(-bound, bound, len(x))

        for dataset, _ in x.groupby('dataset'):
            xd = x.loc[dataset]
            yd = y.loc[dataset]
            l, = self.axes.plot(xd, yd, 'o', mec='w', mew=1)
            self.plot_map[l] = dataset

        if self.figure.canvas is not None:
            self.figure.canvas.draw()

    def button_press_event(self, event):
        if not event.inaxes:
            return
        for plot, dataset in self.plot_map.items():
            contained, info = plot.contains(event)
            if contained:
                if self.selected_feature == 'Threshold':
                    self.selected_point = dataset, None
                else:
                    level = self.data.loc[dataset].iloc[info['ind']].iloc[0].name
                    self.selected_point = dataset, level
