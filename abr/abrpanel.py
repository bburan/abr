from pathlib import Path

import matplotlib as mp
from matplotlib.pylab import setp

rc_path = Path(__file__).parent / 'matplotlibrc'
mp.rc_file(str(rc_path))


class StylePlot:

    HIDDEN = {'alpha': 0}

    def update(self):
        self.update_plot()
        setp(self.plot, **self.get_style())

    def get_style(self):
        raise NotImplementedError

    def update_plot(self):
        pass


class PointPlot(StylePlot):

    PEAK = {
        'linestyle':        ' ',
        'marker':           'o',
        'zorder':           20,
        'alpha':            1,
        'markersize':       8,
        'markeredgewidth':  1,
        'markeredgecolor':  (0, 0, 0)
    }

    PEAK_FADED = {
        'linestyle':        ' ',
        'marker':           'o',
        'zorder':           20,
        'alpha':            0.5,
        'markersize':       8,
        'markeredgewidth':  1,
        'markeredgecolor':  (0, 0, 0)
    }

    VALLEY = {
        'linestyle':        ' ',
        'marker':           '^',
        'zorder':           20,
        'alpha':            1,
        'markersize':       9,
        'markeredgewidth':  1,
        'markeredgecolor':  (0, 0, 0)
    }

    TOGGLE = {
        'linestyle':        ' ',
        'marker':           's',
        'zorder':           100,
        'alpha':            1,
        'markersize':       8,
        'markeredgewidth':  1,
        'markerfacecolor':  (1, 1, 1),
        'markeredgecolor':  (0, 0, 0)
    }

    COLORS = [(1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)]

    def __init__(self, parent, figure, point):
        self.figure = figure
        self.parent = parent
        self.point = point
        self.plot, = self.figure.plot(0, 0, transform=parent.transform,
                                      clip_on=False, picker=10)
        self.current = False
        self.update()

    def get_style(self):
        # Hide subthreshold points
        if self.parent.waveform.is_subthreshold():
            return self.HIDDEN

        # Return toggled value
        if self.current and self.parent.current:
            return self.TOGGLE

        # Fallback to this
        style = self.PEAK if self.point.is_peak() else self.VALLEY
        index = self.point.wave_number-1
        c = self.COLORS[self.point.wave_number-1]
        style['c'] = c
        style['markerfacecolor'] = c
        return style

    def update_plot(self):
        self.plot.set_data(self.point.x, self.point.y)

    def remove(self):
        self.plot.remove()


class WaveformPlot(StylePlot):

    CUR_PLOT = {
        'c':            (0, 0, 0),
        'linewidth':    4,
        'linestyle':    '-',
        'zorder':       20,
    }
    PLOT = {
        'c':            (0, 0, 0),
        'linewidth':    2,
        'linestyle':    '-',
        'zorder':       10,
    }
    CUR_SUBTH_PLOT = {
        'c':            (0.75, 0.75, 0.75),
        'linewidth':    4,
        'linestyle':    '-',
        'zorder':       10,
    }
    SUBTH_PLOT = {
        'c':            (0.75, 0.75, 0.75),
        'linewidth':    2,
        'linestyle':    '-',
        'zorder':       10,
    }

    def __init__(self, waveform, axis, transform):
        self.axis = axis
        self.waveform = waveform
        self.current = False
        self.point_plots = {}
        self.transform = transform

        # Create the plot
        self.plot, = self.axis.plot(self.waveform.x, self.waveform.y, 'k-',
                                    transform=transform, clip_on=False,
                                    picker=10)
        self.update()

    STYLE = {
        (True,  True):  CUR_PLOT,
        (True,  False): CUR_SUBTH_PLOT,
        (False, True):  PLOT,
        (False, False): SUBTH_PLOT,
    }

    def get_style(self):
        style = self.current, self.waveform.is_suprathreshold()
        return self.STYLE[style]

    def update(self):
        # Check to see if new points were added (e.g. valleys)
        for key, point in self.waveform.points.items():
            if key not in self.point_plots:
                self.point_plots[key] = PointPlot(self, self.axis, point)

        for key, point_plot in list(self.point_plots.items()):
            point = self.waveform.points.get(key)
            if point is None:
                point_plot.remove()
                del self.point_plots[key]
            elif point != point_plot.point:
                point_plot.point = self.waveform.points[key]

        for p in self.point_plots.values():
            p.update()

        super().update()
