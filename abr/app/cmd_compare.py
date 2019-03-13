import argparse

from atom.api import Bool, Typed, Unicode

import enaml
from enaml.core.api import d_, Declarative
from enaml.qt.qt_application import QtApplication
with enaml.imports():
    from abr.main_window import CompareWindow

from matplotlib import pylab as pl
import numpy as np
import pandas as pd

from . import add_default_arguments, parse_args


class Compare(Declarative):

    data = Typed(pd.DataFrame)
    x_column = d_(Unicode())
    y_column = d_(Unicode())
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


def main():
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


if __name__ == '__main__':
    main()
