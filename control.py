import wx, re, os, operator
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg \
        as FigureCanvas
from matplotlib.figure import Figure

class LazyTree(wx.TreeCtrl):

    def __init__(self, parent, io, id=wx.ID_ANY, pos=wx.DefaultPosition, 
            size=wx.DefaultSize,
            style=wx.TR_DEFAULT_STYLE 
                     | wx.TR_FULL_ROW_HIGHLIGHT
                     | wx.TR_HIDE_ROOT
                     | wx.TR_MULTIPLE
                     | wx.TR_HAS_BUTTONS,
            root=None,
             **kwargs):

        wx.TreeCtrl.__init__(self, parent, id, pos, size, style, **kwargs) 

        #Loads images for displaying tree
        isz = (16,16)
        il = wx.ImageList(isz[0], isz[1])
        icons = {}
        bm = wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz)
        icons['fldridx'] = il.Add(bm)
        #bm = wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz)
        bm = wx.ArtProvider_GetBitmap(wx.ART_FOLDER_OPEN, wx.ART_OTHER, isz)
        icons['fldropenidx'] = il.Add(bm)
        bm = wx.ArtProvider_GetBitmap(wx.ART_WARNING, wx.ART_OTHER, isz)
        icons['fileidx'] = il.Add(bm)
        bm = wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz)
        icons['fileprocessedidx'] = il.Add(bm)
        self.SetImageList(il)
        self.il = il
        self.icons = icons

        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.on_collapse)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.on_expand)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.start_drag)

        self._io = io
        self.root = root
        #self.buildtree()

    def OnCompareItems(self, item1, item2):
        key1 = self.GetPyData(item1)['sort_key']
        key2 = self.GetPyData(item2)['sort_key']

        if key1 > key2: return 1
        elif key1 < key2: return -1
        else: return 0

    def start_drag(self, event):
        item_ids = self.GetSelections()

        dataobject = wx.FileDataObject()
        for item_id in item_ids:
            data = self.GetPyData(item_id)
            if data['has_children']:
                data = self._io.listall(data['data'])
                data.sort(key=operator.itemgetter('sort_key'))
                for d in data:
                    dataobject.AddFile(d['data_string'])
            else:
                dataobject.AddFile(data['data_string'])

        dropsource = wx.DropSource(self)
        dropsource.SetData(dataobject)
        dropsource.DoDragDrop(True)

    def set_root(self, root):
        self._root = root
        self.DeleteAllItems()
        self.buildtree()

    def get_root(self):
        try: return self._root
        except AttributeError: return None

    root = property(get_root, set_root, None, None)

    def on_collapse(self, event):
        item_id = event.GetItem()
        if not item_id.IsOk():
            item_id = self.tree.GetSelection()
        old_pydata = self.GetPyData(item_id)
        if old_pydata['expanded'] == True:
            self.DeleteChildren(item_id)
            self.extendtree(item_id)
            old_pydata['expanded'] = False
            self.SetPyData(item_id, old_pydata)

    def on_expand(self, event):
        item_id = event.GetItem()
        if not item_id.IsOk():
            item_id = self.tree.GetSelection()

        old_pydata = self.GetPyData(item_id)
        if old_pydata['expanded'] == False:
            self.DeleteChildren(item_id)
            self.extendtree(item_id)
            old_pydata['expanded'] = True
            self.SetPyData(item_id, old_pydata)

    def buildtree(self):
        """PyData object consists of a nested tuple in the format 
        ((display_string, access_key, sort_key, children), expanded_flag)
        """
        root_data = {'display': '', 'data': self.root, 'sort_key': (), 
                'has_children': 1, 'data_string': '', 'expanded': True}
        self.root_id = self.AddRoot(root_data['display'])
        self.SetPyData(self.root_id, root_data)
        self.extendtree(self.root_id)
        self.SortChildren(self.root_id)

    def extendtree(self, parent_id):
        wx.SetCursor(wx.StockCursor(wx.CURSOR_WAIT))
        node_data = self.GetPyData(parent_id)['data']
        subnodes = self._io.list(node_data)

        if subnodes is None: return

        for child in subnodes:
            child_id = self.AppendItem(parent_id, child['display'])
            if child['has_children']:
                child['expanded'] = False
                self.SetItemImage(child_id, self.icons['fldridx'],
                        wx.TreeItemIcon_Normal)
                self.SetItemImage(child_id, self.icons['fldropenidx'],
                        wx.TreeItemIcon_Expanded)
                self.SetItemHasChildren(child_id, True)
            else:
                child['expanded'] = True
                if child['processed']:
                    icon = self.icons['fileprocessedidx']
                else:
                    icon = self.icons['fileidx']
                self.SetItemImage(child_id, icon, wx.TreeItemIcon_Normal)
            self.SetPyData(child_id, child)
        self.SortChildren(parent_id)

#----------------------------------------------------------------------------

class PhysiologyFilePanel(wx.Panel):

    def __init__(self, *args, **kwargs):

        wx.Panel.__init__(self, *args, **kwargs)

        self.__filebrowse = filebrowse.DirBrowseButton(self, wx.ID_ANY,
                labelText='', changeCallback=self.__filebrowse) 

        filefilter = re.compile('^ABR-[0-9]+-[0-9]+$') 
        self.__filetree = LazyFileTree(self, filter=filefilter.match,
                sort_key=sort_runs)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.__filebrowse, 0, wx.EXPAND)
        sizer.Add(self.__filetree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.Fit()

    def __filebrowse(self, evt):
        if os.path.isdir(evt.GetString()):
            self.__filetree.rootpath = evt.GetString()

class MatplotlibPanel(wx.Panel):

    #Defines plot styles
    AXIS_LABEL = {
            'fontsize':     16,
            'fontweight':   'bold'
        }
    PLOT_TEXT = {
            'fontsize':     10,
            'fontweight':   'bold'
        }

    def __init__(self, parent, xlabel, ylabel, id=wx.ID_ANY, figsize=(4,5)):
        wx.Panel.__init__(self, parent)
        self.figure = Figure(figsize,75)
        self.canvas = MatplotlibCanvas(self, -1, self.figure)
        self.subplot = self.figure.add_subplot(111)
        self.subplot.set_xlabel(xlabel, MatplotlibPanel.AXIS_LABEL)
        self.subplot.set_ylabel(ylabel, MatplotlibPanel.AXIS_LABEL)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        self.SetSizer(sizer)

    def set_ylabel(self, text):
        self.subplot.set_ylabel(text, MatplotlibPanel.AXIS_LABEL)

class MatplotlibCanvas(FigureCanvas):
    
    def __init__(self, parent, figure, id=wx.ID_ANY):
        #FigureCanvas.__init__(self, parent, figure, style=wx.WANTS_CHARS)
        FigureCanvas.__init__(self, parent, figure, id)
        self._drawn = 0
        
        '''Need to force the matplotlib canvas to take characters which we can
        then process.  For some reason, if interactive mode is turned on, we
        cannot detect keydown events.  We don't really need interactive mode
        anyway, so we will leave it off.'''
        style = self.GetWindowStyle() | wx.WANTS_CHARS
        self.SetWindowStyle(style)
        
    def _onPaint(self, evt):
        '''Prevents excessive repainting of canvas once view is initialized.
        Makes resizing and dragging of canvas much smoother.'''
        #if not self._isRealized:
            #self.realize()
        if self._drawn < 2:
            #self.draw(repaint = False)
            self.draw()
            self._drawn += 1
        self.gui_repaint(drawDC=wx.PaintDC(self))
