import os
import wx
import wx.aui

from control import MatplotlibPanel
from presenter import WaveformPresenter
from interactor import WaveformInteractor

from config import DefaultValueHolder
import filter_EPL_LabVIEW_ABRIO_File as peakio


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

    def load(self, filenames, invert=False):
        for filename in filenames:
            self.load_file(filename, invert)

    def load_file(self, filename, invert=False):
        try:
            # XOR input
            invert = self.options.invert ^ invert
            if self.options.filter:
                filter_settings = {
                    'ftype': 'butter',
                    'lowpass': self.options.lowpass,
                    'highpass': self.options.highpass,
                    'order': self.options.order,
                }
            else:
                filter_settings = None
            model = peakio.load(filename, invert, filter_settings)
            view = MatplotlibPanel(self, 'Time (msec)', 'Amplitude (uV)')
            interactor = WaveformInteractor()
            WaveformPresenter(model, view, interactor)
            name = '%s %.2f kHz' % (os.path.split(filename)[1], model.freq)
            self.AddPage(view, name, select=True)
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
        self.parent.load(filenames, self.invert)

    def OnEnter(self, x, y, meta):
        if meta == wx.DragCopy:
            self.invert = True
        else:
            self.invert = False
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
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

    def OnQuit(self, evt):
        dlg = wx.MessageDialog(None, 'Are you sure you want to quit?',
                               'Question',
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        response = dlg.ShowModal()

        if response == wx.ID_YES:
            # Persist the location and size of the window
            maximized = self.IsMaximized()
            fpos = self.GetPosition()
            fsize = self.GetSize()
            self._window.SetVariables(width=fsize[0], height=fsize[1],
                                      x=fpos[0], y=fpos[1],
                                      maximized=int(maximized))
            self._window.UpdateConfig()
            self.Destroy()


class PhysiologyFrame(PersistentFrame):

    def __init__(self, options, name="Waveform Analysis", parent=None, *args,
                 **kwargs):

        PersistentFrame.__init__(self, name, parent, *args, **kwargs)
        self.options = options

        # Initialize menu
        menubar = wx.MenuBar()
        file = wx.Menu()
        ID_CLOSE_TAB = wx.NewId()
        file.Append(wx.ID_OPEN, 'Open &File\tCtrl+O', 'Open File')
        file.Append(ID_CLOSE_TAB, 'Close &Tab\tCtrl+W', 'Close Tab')
        file.AppendSeparator()
        file.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit Application')
        file.Append(wx.ID_ABOUT, '&About\tCtrl+A', 'About')
        menubar.Append(file, '&File')

        self.SetMenuBar(menubar)

        # Menu events
        self.Bind(wx.EVT_MENU, self.OnOpenFile, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnCloseTab, id=ID_CLOSE_TAB)

        # Initialize manager and panels
        self.__mgr = wx.aui.AuiManager()
        self.__mgr.SetManagedWindow(self)
        self._nb = PhysiologyNotebook(options, self)
        self.__mgr.AddPane(self._nb, wx.aui.AuiPaneInfo().
                           Name('notebook').Center().CloseButton(False).
                           MaximizeButton(True))
        self.__mgr.Update()

        self.CreateStatusBar()
        self.Show()

    def OnCloseTab(self, evt):
        if self._nb.PageCount:
            self._nb.DeletePage(self._nb.GetSelection())

    def OnAbout(self, evt):
        info = wx.AboutDialogInfo()
        info.Name = "Evoked Waveform Analysis"
        info.Version = "1.0"
        info.Copyright = "(C) 2012 Brad Buran"
        info.WebSite = "http://bradburan.com"
        wx.AboutBox(info)

    def OnOpenFile(self, evt):
        style = wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR
        if self.options.directory is not None:
            dlg = wx.FileDialog(self, "Choose files", style=style,
                                defaultDir=self.options.directory)
        else:
            dlg = wx.FileDialog(self, "Choose files", style=style)
        if dlg.ShowModal() == wx.ID_OK:
            self._nb.load(dlg.GetFilenames())
        dlg.Destroy()
