import os
import wx
import wx.aui

from abr.control import MatplotlibPanel
from abr.presenter import WaveformPresenter
from abr.interactor import WaveformInteractor

from abr.config import DefaultValueHolder
from abr.parsers import registry


def create_presenter(model, frame, options, app=None):
    view = MatplotlibPanel(frame, 'Time (msec)', 'Amplitude (uV)')
    interactor = WaveformInteractor()
    presenter = WaveformPresenter(view, interactor, options, app)
    presenter.load(model)
    return presenter


class PhysiologyNotebook(wx.aui.AuiNotebook):

    def __init__(self, options, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.aui.AUI_NB_DEFAULT_STYLE,
                 **kwargs):

        super(PhysiologyNotebook, self).__init__(parent, id, pos, size, style,
                                                 **kwargs)

        self.options = options

        # Allow users to drag-and-drop one or more into the window to open them
        dt = PhysiologyNbFileDropTarget(self)
        self.SetDropTarget(dt)

    def load(self, filenames):
        for filename in filenames:
            self.load_file(filename)

    def load_file(self, filename):
        try:
            models = registry.load(filename, self.options)
            for model in models:
                presenter = create_presenter(model, self, self.options)
                name = '%s %.2f kHz' % (os.path.split(filename)[1], model.freq)
                self.AddPage(presenter.view, name, select=True)
        except IOError, e:
            dlg = wx.MessageDialog(self, str(e), 'File Error',
                                   wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()


class PhysiologyNbFileDropTarget(wx.FileDropTarget):
    '''
    Allows the user to drop one or more files onto the canvas for analysis.
    '''

    def __init__(self, parent):
        wx.FileDropTarget.__init__(self)
        self.parent = parent

    def OnDropFiles(self, x, y, filenames):
        self.parent.load(filenames)

    def OnEnter(self, x, y, meta):
        return wx.DragMove


class PersistentFrame(wx.Frame):
    '''
    Remembers the prior window settings (width, height and window position)
    across sessions.
    '''

    def __init__(self, name=None, parent=None, *args, **kwargs):
        self._window = DefaultValueHolder('PersistentFrame', name)
        self._window.SetVariables(width=600, height=800, x=0, y=0, maximized=0)
        self._window.InitFromConfig()

        size = (self._window.width, self._window.height)
        pos = (self._window.x, self._window.y)
        wx.Frame.__init__(self, parent, size=size, pos=pos, *args, **kwargs)
        if self._window.maximized:
            self.Maximize()
        self.CreateStatusBar()


class PhysiologyFrame(PersistentFrame):

    def __init__(self, options=None, name="Waveform Analysis", parent=None,
                 *args, **kwargs):

        PersistentFrame.__init__(self, name, parent, *args, **kwargs)
        if options is None:
            options = {}
        self.options = options

        # Initialize menu
        menubar = wx.MenuBar()
        file = wx.Menu()
        file.Append(wx.ID_OPEN, 'Open &File\tCtrl+O', 'Open File')
        menubar.Append(file, '&File')

        self.SetMenuBar(menubar)

        # Menu events
        self.Bind(wx.EVT_MENU, self.OnOpenFile, id=wx.ID_OPEN)

        # Initialize manager and panels
        self.__mgr = wx.aui.AuiManager()
        self.__mgr.SetManagedWindow(self)
        self._nb = PhysiologyNotebook(options, self)
        self.__mgr.AddPane(self._nb, wx.aui.AuiPaneInfo().
                           Name('notebook').Center().CloseButton(False).
                           MaximizeButton(True))
        self.__mgr.Update()

        self.Show()

    def OnOpenFile(self, evt):
        style = wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR
        dlg = wx.FileDialog(self, "Choose files", style=style)
        if dlg.ShowModal() == wx.ID_OK:
            self._nb.load(dlg.GetFilenames())
        dlg.Destroy()
