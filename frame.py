import re, os, string, sys, dircache
import wx, wx.aui
import wx.lib.filebrowsebutton as filebrowse
import wx.lib.pubsub as pubsub
import wx.html

from control import MatplotlibPanel, LazyTree
from presenter import WaveformPresenter
from interactor import KeyInteractor, WaveformInteractor

from config import DefaultValueHolder
import filter_EPL_LabVIEW_ABRIO_File as peakio

def listdir(dir, match, incdirs=False):
    if incdirs:
        return [os.path.join(dir, f) for f in dircache.listdir(dir) if \
                match(f) or os.path.isdir(os.path.join(dir, f))]
    else:
        return [os.path.join(dir, f) for f in dircache.listdir(dir) if \
                match(f)]

#----------------------------------------------------------------------------

def loadmodel(fname, invert):
    filter = DefaultValueHolder("PhysiologyNotebook", "filter")
    filter.SetVariables(ftype="butterworth", fl=10000, fh=200)
    filter.InitFromConfig()
    #fdict = {'ftype': filter.ftype, 'fh': filter.fh, 'fl': filter.fl}
    fdict = {'ftype': filter.ftype, 'W': (filter.fh, filter.fl)}
    return peakio.load(fname, invert, fdict)

#----------------------------------------------------------------------------

class PersistentFrame(wx.Frame):

    def __init__(self, name=None, parent=None, *args, **kwargs): 

        self.options = DefaultValueHolder('PhysiologyNotebook', name)
        self.options.SetVariables(width=600,height=800,x=0,y=0,maximized=0)
        self.options.InitFromConfig()

        size = (self.options.width, self.options.height)
        pos = (self.options.x, self.options.y)
        wx.Frame.__init__(self, parent, size=size, pos=pos, *args, **kwargs)
        if self.options.maximized:
            self.Maximize()
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

    def OnQuit(self, evt):
        dlg = wx.MessageDialog(None, 'Are you sure you want to quit?',
              'Question', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        response = dlg.ShowModal()
        if response == wx.ID_YES:
            maximized = self.IsMaximized()
            #We want the pos and size of the unmaximized window
            self.Maximize(False)
            fpos = self.GetPosition()
            fsize = self.GetSize()
            self.options.SetVariables(width=fsize[0], height=fsize[1],
                    x=fpos[0], y=fpos[1], maximized=int(maximized))
            self.options.UpdateConfig()
            self.Destroy()
        evt.Skip()

#----------------------------------------------------------------------------

class PhysiologyNotebook(wx.aui.AuiNotebook):

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
            size=wx.DefaultSize, style=wx.aui.AUI_NB_DEFAULT_STYLE, **kwargs):

        wx.aui.AuiNotebook.__init__(self, parent, id, pos, size, style,
                **kwargs)
        dt = PhysiologyNbFileDropTarget(self)
        self.SetDropTarget(dt)

    def load(self, data, invert=False):
        wx.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        for d in data:
            self.loadser(d, invert)

    def loadser(self, fname, invert=False):
        try:
            model = loadmodel(fname, invert)
            view = MatplotlibPanel(self, 'Time (msec)', 'Amplitude (uV)', 
                    figsize=(9,8))
            WaveformPresenter(model, view, WaveformInteractor())
            name = '%s %.2f kHz' % (os.path.split(fname)[1], model.freq)
            self.AddPage(view, name, select=True)
            self.GetTopLevelParent().SetStatusText('Loaded file %s' % name) 
        except IOError, e:
            dlg = wx.MessageDialog(self, e.message, 'File Error',
                    wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

#----------------------------------------------------------------------------

class PhysiologyNbFileDropTarget(wx.FileDropTarget):

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

#----------------------------------------------------------------------------

class PhysiologyFrame(PersistentFrame):

    def __init__(self, name="InteractiveFrame", parent=None, splash=False, 
            *args, **kwargs):

        if splash:
            splash = PhysiologySplashScreen(duration=3000)
            splash.Show()

        PersistentFrame.__init__(self, name, parent, *args, **kwargs)

        #Initialize menu
        menubar = wx.MenuBar()
        file = wx.Menu()
        ID_SET_DIR = wx.NewId()
        ID_SET_OPTIONS = wx.NewId()
        ID_CLOSE_TAB = wx.NewId()
        file.Append(ID_SET_DIR, 'Open &Directory\tCtrl+D', 'Open Directory') 
        file.Append(wx.ID_OPEN, 'Open &File\tCtrl+F', 'Open File')
        file.Append(ID_SET_OPTIONS, '&Options\tCtrl+O', 'Options')
        file.Append(ID_CLOSE_TAB, 'Close &Tab\tCtrl+W', 'Close Tab')
        file.AppendSeparator()
        file.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit Application')
        menubar.Append(file, '&File')

        help = wx.Menu()
        ID_DISPLAY_HELP = wx.NewId()
        help.Append(ID_DISPLAY_HELP, '&Help\tCtrl+H', 'Help')
        help.AppendSeparator()
        help.Append(wx.ID_ABOUT, '&About\tCtrl+A', 'About')
        menubar.Append(help, '&Help')
        self.SetMenuBar(menubar)

        #Menu events
        self.Bind(wx.EVT_MENU, self.OnSetDir, id=ID_SET_DIR)
        self.Bind(wx.EVT_MENU, self.OnSetOptions, id=ID_SET_OPTIONS)
        self.Bind(wx.EVT_MENU, self.OnOpenFile, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnCloseTab, id=ID_CLOSE_TAB)
        self.Bind(wx.EVT_MENU, self.OnDisplayHelp, id=ID_DISPLAY_HELP)

        #Initialize manager and panels
        self.__mgr = wx.aui.AuiManager()
        self.__mgr.SetManagedWindow(self)

        self.__nb = PhysiologyNotebook(self)
        filefilter = re.compile('^ABR-[0-9]+-[0-9]+(\\.dat)?$') 

        foptions = DefaultValueHolder("PhysiologyNotebook", "file")
        foptions.SetVariables(startdir=".")
        foptions.InitFromConfig()
        #rootpath = foptions.startdir
        rootpath = None

        self.__filetree = LazyTree(self, io=peakio, root=rootpath)

        self.__mgr.AddPane(self.__nb, wx.aui.AuiPaneInfo().
                Name('notebook').Center().CloseButton(False).
                MaximizeButton(True))
        self.__mgr.AddPane(self.__filetree, wx.aui.AuiPaneInfo().
                Name('files').Left().CloseButton(False).MaximizeButton(False).
                BestSize((200,400)))

        self.__mgr.Update()

        self.help = wx.html.HtmlHelpController(style=
                wx.html.HF_CONTENTS |
                wx.html.HF_PRINT |
                wx.html.HF_MERGE_BOOKS
                )
        #self.help.AddBook('help/help.hhp')

        self.CreateStatusBar()
        self.SetStatusText('Please drag and drop files to canvas')
        self.Show()

    def OnDisplayHelp(self, evt):
        self.help.DisplayContents()

    def OnCloseTab(self, evt):
        self.__nb.DeletePage(self.__nb.GetSelection())

    def OnAbout(self, evt):
        info = wx.AboutDialogInfo()
        info.Name = "ABR Peak Analysis"
        info.Version = "0.8 RC 1"
        info.Copyright = "(C) 2007 Speech and Hearing Bioscience and Technology"
        info.WebSite = "http://web.mit.edu/shbt"
        info.Developers = ["Brad Buran"]
        wx.AboutBox(info)

    def OnSetOptions(self, evt):
        dlg = PhysiologyOptions(self, wx.ID_ANY, "Options")
        dlg.CenterOnScreen()
        val = dlg.ShowModal()
        evt.Skip()

    def OnSetDir(self, evt):
        dlg = wx.DirDialog(self, "Choose a directory:",
                style=wx.DD_DIR_MUST_EXIST | wx.DD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.__filetree.root = dlg.GetPath()
        dlg.Destroy()
        evt.Skip()

    def OnOpenFile(self, evt):
        wildcard = 'ABR-*-*'
        dlg = wx.FileDialog(self, "Choose a file:", wildcard=wildcard,
                style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            self.__nb.loadfiles(dlg.GetFilenames())
        dlg.Destroy()    
        evt.Skip()

    def OnSave(self, evt):
        dialog = wx.MessageDialog(None, 'Not implemented yet!!!',
                'ERROR', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        dlg.Destroy()
        evt.Skip()

#----------------------------------------------------------------------------

class PhysiologyOptions(wx.Dialog):

    def __init__(self, parent, id, title, size=wx.DefaultSize,
            pos=wx.DefaultPosition, style=wx.DEFAULT_DIALOG_STYLE):

        self.filter = DefaultValueHolder('PhysiologyNotebook','filter')
        self.filter.SetVariables(ftype='Butterworth', fl=10000, fh=200)
        self.filter.InitFromConfig()
        self.file = DefaultValueHolder('PhysiologyNotebook','file')
        self.file.SetVariables(startdir='.')
        self.file.InitFromConfig()

        self.iofilter = DefaultValueHolder('PhysiologyNotebook','iofilter')
        self.iofilter.SetVariables(method='database')
        self.iofilter.InitFromConfig()

        filter = self.filter
        file = self.file

        ftypes = ['None', 'Bessel', 'Butterworth']
        pre = wx.PreDialog()
        pre.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        pre.Create(parent, id, title, pos, size, style)
        self.PostCreate(pre)

        sizer = wx.BoxSizer(wx.VERTICAL)
        
        #Default directory
        dbox = wx.StaticBox(self, wx.ID_ANY, "Default Directory")
        dsizer = wx.StaticBoxSizer(dbox, wx.VERTICAL)
        self.dbb = filebrowse.DirBrowseButton(self, wx.ID_ANY, size=(550,-1),
                startDirectory=file.startdir)
        self.dbb.SetValue(file.startdir)
        dsizer.Add(self.dbb, 0, wx.EXPAND|wx.ALL, 5)

        #Filter options
        fbox = wx.StaticBox(self, wx.ID_ANY, "Filtering Options")
        fsizer = wx.StaticBoxSizer(fbox, wx.VERTICAL)
        box = wx.BoxSizer(wx.HORIZONTAL)

        #Filter type
        label = wx.StaticText(self, wx.ID_ANY, "Filter type:")
        box.Add(label, 0, wx.ALL, 5)
        self.ftype = wx.Choice(self, wx.ID_ANY, choices=ftypes)
        self.ftype.SetSelection(self.ftype.FindString(filter.ftype))
        box.Add(self.ftype, 0, wx.EXPAND|wx.ALL, 5)

        self.ftype.Bind(wx.EVT_CHOICE, self.ftype_choice)

        #Highpass
        label = wx.StaticText(self, wx.ID_ANY, "Highpass Cutoff (Hz):")
        box.Add(label, 0, wx.ALL, 5)
        self.fh = wx.TextCtrl(self, wx.ID_ANY, str(filter.fh),
            size=(75,-1), validator=FrequencyValidator())
        box.Add(self.fh, 0, wx.ALL, 5)

        #Lowpass
        label = wx.StaticText(self, wx.ID_ANY, "Lowpass Cutoff (Hz):")
        box.Add(label, 0, wx.ALL, 5)
        self.fl = wx.TextCtrl(self, wx.ID_ANY, str(filter.fl),
            size=(75,-1), validator=FrequencyValidator())
        box.Add(self.fl, 0, wx.ALL, 5)
        fsizer.Add(box, 0, wx.GROW|wx.ALL, 5)

        if filter.ftype == 'None':
            self.fh.Disable()
            self.fl.Disable()

        line = wx.StaticLine(self, wx.ID_ANY, size=(20,-1), style=wx.LI_HORIZONTAL)

        sizer.Add(dsizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(fsizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(line, 0, wx.GROW, wx.RIGHT|wx.TOP, 5)

        #Buttons
        btnsizer = wx.StdDialogButtonSizer()
        self.ok = wx.Button(self, wx.ID_OK)
        self.ok.SetDefault()
        btnsizer.AddButton(self.ok)

        self.cancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(self.cancel)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.ok.Bind(wx.EVT_BUTTON, self.OnOk)

    def OnOk(self, evt):
        if self.Validate():
            self.EndModal(wx.ID_OK)
            self.file.SetVariables(startdir=self.dbb.GetValue())
            self.file.UpdateConfig()
            self.filter.SetVariables(ftype=self.ftype.GetString(self.ftype.GetSelection()),
                    fl=int(self.fl.GetValue()), fh=int(self.fh.GetValue()))
            self.filter.UpdateConfig()
        
    def Validate(self):
        msg = []
        flag = False

        if not hasattr(self, 'dbb_color'):
            self.dbb_color = self.dbb.GetBackgroundColour()
        if not hasattr(self, 'txtctrl_color'):
            self.txtctrl_color = self.fl.GetBackgroundColour()

        if not os.path.exists(self.dbb.GetValue()):
            msg.append("Directory does not exist")
            flag = True
            self.dbb.SetBackgroundColour("Pink")
        else:    
            self.dbb.SetBackgroundColour(self.dbb_color)

        fl = self.fl.GetValue()
        fh = self.fh.GetValue()
        ftype = self.ftype.GetString(self.ftype.GetSelection())

        if ftype != 'None' and fl == '':
            msg.append("Must specify a value for the lowpass frequency")
            self.fl.SetBackgroundColour("Pink")
            flag = True
        else:    
            self.fl.SetBackgroundColour(self.txtctrl_color)
        if ftype != 'None' and fh == '':
            msg.append("Must specify a value for the highpass frequency")
            self.fh.SetBackgroundColour("Pink")
            flag = True
        else:    
            self.fh.SetBackgroundColour(self.txtctrl_color)

        if fl != '' and fh != '' and ftype != 'None':
            if not int(self.fl.GetValue()) > int(self.fh.GetValue()):
                msg.append("Lowpass freq must be greater than highpass freq")
                flag = True
                self.fl.SetBackgroundColour("Pink")
                self.fh.SetBackgroundColour("Pink")
            else:    
                self.fl.SetBackgroundColour(self.txtctrl_color)
                self.fh.SetBackgroundColour(self.txtctrl_color)

        if flag:
            self.Refresh()
            wx.MessageBox("\n".join(msg), "Error")

        return not flag    

    def ftype_choice(self, evt):
        if evt.GetString() == 'None':
            self.fh.Disable()
            self.fl.Disable()
        else:
            self.fh.Enable()
            self.fl.Enable()

#----------------------------------------------------------------------------

class PhysiologyValidator(wx.PyValidator):

    def __init__(self):
        wx.PyValidator.__init__(self)

    def Clone(self):
        return PhysiologyValidator()

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

#----------------------------------------------------------------------------
class FrequencyValidator(PhysiologyValidator):

    def __init__(self):
        PhysiologyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()
        
        for x in val:
            if x not in string.digits:
                return False
        return True

    def Clone(self):
        return FrequencyValidator()

    def OnChar(self, evt):
        key = evt.GetKeyCode()
        
        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            evt.Skip()
            return

        if chr(key) in string.digits:
            evt.Skip()
            return

        return

#----------------------------------------------------------------------------

class FileValidator(PhysiologyValidator):

    def __init__(self):
        wx.PyValidator.__init__(self)

    def Clone(self):
        return FileValidator()

    def Validate(self, win):
        tc = self.GetWindow()
        val = tc.GetValue()
        return os.path.exists(val)

#----------------------------------------------------------------------------

class PhysiologySplashScreen(wx.SplashScreen):

    def __init__(self, parent=None, duration=3000):
        splash_bitmap = os.path.join(os.path.split(sys.argv[0])[0], "splash.png")
        bitmap = wx.Image(name=splash_bitmap).ConvertToBitmap()
        style = wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT
        wx.SplashScreen.__init__(self, bitmap, style, duration, parent)
        self.Bind(wx.EVT_CLOSE, self.OnExit)

    def OnExit(self, evt):
        self.Hide()
        evt.Skip()

#----------------------------------------------------------------------------

class AutomaticFrame(PersistentFrame):

    def __init__(self, runs, name="AutomaticFrame", parent=None,
            params=None, *args, **kwargs):

        PersistentFrame.__init__(self, name, parent, *args, **kwargs)

        #Initialize menu
        menubar = wx.MenuBar()
        file = wx.Menu()
        file.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit Application')
        menubar.Append(file, '&File')
        self.SetMenuBar(menubar)

        #Menu events
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        self.view = MatplotlibPanel(self, 'Time (msec)', 'Amplitude (uV)', 
                figsize=(9,8))
        pubsub.Publisher().subscribe(self.next, "DATA SAVED")
        pubsub.Publisher().subscribe(self.next, "NEXT")
        pubsub.Publisher().subscribe(self.undo, "UNDO")

        self.CreateStatusBar()

        self.runs = runs
        self.current = -1
        self.params = params

        self.next()
        self.Show()

    def next(self, evt=None):
        self.view.subplot.cla()
        self.current += 1
        if self.current >= len(self.runs):
            self.SetStatusText('No more runs to analyze')
        else:
            model = loadmodel(self.runs[self.current]['data'],
                    self.params.invert)
            self.presenter = WaveformPresenter(None, self.view,
                    WaveformInteractor())
            self.presenter.load(model, self.params)
            self.SetStatusText('Loaded %r - %.2f kHz' % (model.location,
                model.freq)) 

    def undo(self, evt=None):
        if self.current > 0:
            self.current -= 2
            self.next()

