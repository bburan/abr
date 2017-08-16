import wx
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg \
    as FigureCanvas


class MatplotlibPanel(wx.Panel):
    # Adapted from http://www.scipy.org/Matplotlib_figure_in_a_wx_panel

    # Defines plot styles
    AXIS_LABEL = {
        'fontsize':     16,
        'fontweight':   'bold'
    }
    PLOT_TEXT = {
        'fontsize':     10,
        'fontweight':   'bold'
    }

    def __init__(self, parent, xlabel, ylabel, id=wx.ID_ANY, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.parent = parent
        self.figure = Figure(None, None)
        self.canvas = FigureCanvas(self, -1, self.figure)

        '''Need to force the matplotlib canvas to take characters which we can
        then process.  For some reason, if interactive mode is turned on, we
        cannot detect keydown events.  We don't really need interactive mode
        anyway, so we will leave it off.
        '''
        style = self.canvas.GetWindowStyle() | wx.WANTS_CHARS
        self.canvas.SetWindowStyle(style)

        self.subplot = self.figure.add_axes([0.1, 0.1, 0.8, 0.8])

        self._resizeflag = False
        self.Bind(wx.EVT_IDLE, self._onIdle)
        self.Bind(wx.EVT_SIZE, self._onSize)

    def _onIdle(self, evt):
        if self._resizeflag:
            self._resizeflag = False
            self._SetSize()

    def _onSize(self, evt):
        self._resizeflag = True

    def _SetSize(self):
        pixels = tuple(self.parent.GetClientSize())
        self.SetSize(pixels)
        self.canvas.SetSize(pixels)
        dpi = self.figure.get_dpi()
        self.figure.set_size_inches(float(pixels[0])/dpi, float(pixels[1])/dpi)

    def set_ylabel(self, text):
        self.subplot.set_ylabel(text, self.AXIS_LABEL)

    def set_title(self, text):
        self.subplot.set_title(text, self.AXIS_LABEL)
