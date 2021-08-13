import argparse
from collections import Counter
from pathlib import Path

from matplotlib import pylab as pl
from numpy import random
import pandas as pd
from scipy import stats

from atom.api import Bool, Typed, Str
import enaml
from enaml.application import deferred_call
from enaml.core.api import d_, Declarative
from enaml.qt.qt_application import QtApplication

with enaml.imports():
    from abr.launch_window import LaunchWindow
    from abr.main_window import (CompareWindow, DNDWindow, load_files,
                                 SerialWindow)
    from abr.presenter import SerialWaveformPresenter, WaveformPresenter


from abr.parsers import Parser


P_LATENCIES = {
    1: stats.norm(1.5, 0.5),
    2: stats.norm(2.5, 1),
    3: stats.norm(3.0, 1),
    4: stats.norm(4.0, 1),
    5: stats.norm(5.0, 2),
}


def add_default_arguments(parser, waves=True):
    parser.add_argument('--nofilter', action='store_false', dest='filter',
                        default=True, help='Do not filter waveform')
    parser.add_argument('--lowpass',
                        help='Lowpass cutoff (Hz), default 3000 Hz',
                        default=3000, type=float)
    parser.add_argument('--highpass',
                        help='Highpass cutoff (Hz), default 300 Hz',
                        default=300, type=float)
    parser.add_argument('--order',
                        help='Filter order, default 1st order', default=1,
                        type=int)
    parser.add_argument('--parser', default='HDF5', help='Parser to use')
    parser.add_argument('--user', help='Name of person analyzing data')
    if waves:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--threshold-only', action='store_true')
        group.add_argument('--all-waves', action='store_true')
        group.add_argument('--waves', type=int, nargs='+')


def parse_args(parser, waves=True):
    options = parser.parse_args()
    exclude = ('filter', 'lowpass', 'highpass', 'order', 'parser', 'user',
               'waves', 'all_waves', 'threshold_only')
    new_options = {k: v for k, v in vars(options).items() if k not in exclude}
    filter_settings = None
    if options.filter:
        filter_settings = {
            'lowpass': options.lowpass,
            'highpass': options.highpass,
            'order': options.order,
        }
    new_options['parser'] = Parser(options.parser, filter_settings,
                                   options.user)

    if not waves:
        return new_options

    if options.all_waves:
        waves = [1, 2, 3, 4, 5]
    elif options.threshold_only:
        waves = []
    else:
        waves = options.waves[:]
    new_options['latencies'] = {w: P_LATENCIES[w] for w in waves}
    return new_options


def main_launcher():
    app = QtApplication()
    window = LaunchWindow()
    window.show()
    app.start()
    app.stop()


def main_gui():
    parser = argparse.ArgumentParser('abr_gui')
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parse_args(parser)

    app = QtApplication()
    view = DNDWindow(parser=options['parser'], latencies=options['latencies'])

    filenames = [(Path(f), None) for f in options['filenames']]

    deferred_call(load_files, options['parser'], options['latencies'],
                  filenames, view.find('dock_area'))

    view.show()
    app.start()
    app.stop()


def main_batch():
    parser = argparse.ArgumentParser("abr_batch")
    add_default_arguments(parser)
    parser.add_argument('dirnames', nargs='*')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--skip-errors', action='store_true')
    parser.add_argument('--frequencies', nargs='*', type=float)
    parser.add_argument('--shuffle', action='store_true')
    options = parse_args(parser)
    parser = options['parser']

    unprocessed = []
    for dirname in options['dirnames']:
        files = parser.find_unprocessed(dirname,
                                        frequencies=options['frequencies'])
        unprocessed.extend(files)

    if options['shuffle']:
        random.shuffle(unprocessed)

    if len(unprocessed) == 0:
        print('No files to process')
        return

    if options['list']:
        counts = Counter(f for f, _ in unprocessed)
        for filename, n in counts.items():
            filename = filename.stem
            print(f'{filename} ({n})')
        return

    app = QtApplication()
    presenter = SerialWaveformPresenter(parser=parser,
                                        latencies=options['latencies'],
                                        unprocessed=unprocessed)
    view = SerialWindow(presenter=presenter)
    view.show()
    app.start()
    app.stop()


class Compare(Declarative):

    data = Typed(pd.DataFrame)
    x_column = d_(Str())
    y_column = d_(Str())
    as_difference = d_(Bool(True))
    jitter = d_(Bool(True))
    axes = Typed(pl.Axes)
    figure = Typed(pl.Figure)
    selected = Typed(list)

    def _default_figure(self):
        return pl.Figure()

    def _default_axes(self):
        return self.figure.add_subplot(111)

    def _observe_data(self, event):
        self._update_plot()

    def _observe_x_column(self, event):
        self._update_plot()

    def _observe_y_column(self, event):
        self._update_plot()

    def _observe_as_difference(self, event):
        self._update_plot()

    def _observe_jitter(self, event):
        self._update_plot()

    def _default_x_column(self):
        return self.data.columns[0]

    def _default_y_column(self):
        i = 1 if (len(self.data.columns) > 1) else 0
        return self.data.columns[i]

    def _update_plot(self):
        x = self.data[self.x_column].copy()
        y = self.data[self.y_column].copy()
        if self.as_difference:
            y -= x
        if self.jitter:
            x += np.random.uniform(-1, 1, len(x))
            y += np.random.uniform(-1, 1, len(x))

        self.axes.clear()
        self.axes.plot(x, y, 'ko', picker=4, mec='w', mew=1)
        if self.figure.canvas is not None:
            self.figure.canvas.draw()

    def pick_handler(self, event):
        rows = self.data.iloc[event.ind]
        files = list(rows.index.get_level_values('raw_file'))
        frequencies = list(rows.index.get_level_values('frequency'))
        self.selected = list(zip(files, frequencies))


def main_compare():
    parser = argparse.ArgumentParser("abr_compare")
    add_default_arguments(parser, waves=False)
    parser.add_argument('directory')
    options = parse_args(parser, waves=False)

    data = options['parser'].load_analyses(options['directory'])
    data = data.reset_index(['analyzed_file'], drop=True).unstack('user')
    data = data.sort_index()

    figure, axes = pl.subplots(1, 1)
    compare = Compare(data=data)

    app = QtApplication()
    view = CompareWindow(parser=options['parser'], compare=compare)
    view.show()
    app.start()
    app.stop()
