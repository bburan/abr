import wx
from datatype import Point
import wx.lib.pubsub as pubsub

class KeyInteractor(object):

    KEYS = {
            wx.WXK_LEFT:    'left',
            wx.WXK_RIGHT:   'right',
            wx.WXK_DOWN:    'down',
            wx.WXK_UP:      'up',
            wx.WXK_RETURN:  'return',
            43:             'plus',
            45:             'minus'
        }

    def Install(self, presenter, view):
        self.presenter = presenter
        self.view = view

        #Events to capture
        self.view.canvas.Bind(wx.EVT_KEY_UP, self.__keyup)
        self.view.canvas.Bind(wx.EVT_KEY_DOWN, self.__keydown)
        self.view.canvas.Bind(wx.EVT_IDLE, self.__idle)

    def __idle(self, evt):
        self.presenter.update()

    def __keyup(self, evt):
        self.__dispatch('ku_', evt)

    def __keydown(self, evt):
        self.__dispatch('kd_', evt)

    def __dispatch(self, type, evt):
        keycode = evt.GetKeyCode()
        if keycode in KeyInteractor.KEYS:
            mname = type + KeyInteractor.KEYS[keycode]
            if hasattr(self, mname):
                getattr(self, mname)(evt)
        elif keycode < 256:
            if chr(keycode) in ['1', '2', '3', '4', '5']:
                keychar = chr(keycode)
                mname = type + 'number'
                if hasattr(self, mname):
                    if evt.ShiftDown():
                        polarity = Point.VALLEY
                    else:
                        polarity = Point.PEAK
                    getattr(self, mname)((polarity, int(chr(keycode))))
            else:
                mname = type + chr(keycode).lower()
                if hasattr(self, mname):
                    getattr(self, mname)()

#----------------------------------------------------------------------------

class WaveformInteractor(KeyInteractor):

    def kd_up(self, evt):
        self.presenter.current += 1

    def kd_down(self, evt):
        self.presenter.current -= 1

    def ku_return(self, evt):
        self.presenter.set_threshold()

    def kd_plus(self, evt):
        self.presenter.scale += 1

    def kd_minus(self, evt):
        self.presenter.scale -= 1

    def kd_left(self, evt):
        if evt.ShiftDown():
            move = ('index', -5)
        else:
            move = ('zc', -1)
        self.presenter.move(move)    

    def kd_right(self, evt):
        if evt.ShiftDown():
            move = ('index', 5)
        else:
            move = ('zc', 1)
        self.presenter.move(move)    

    def ku_number(self, value):
        self.presenter.toggle = value
        
    def ku_u(self):
        '''Updates guesses for waveforms further down'''
        self.presenter.update_point()

    def ku_n(self):
        self.presenter.normalized = not self.presenter.normalized

    def ku_s(self):
        self.presenter.save()

    def ku_i(self):    
        self.presenter.guess_n()

    def ku_z(self):
        pubsub.Publisher().sendMessage("UNDO")

    def ku_p(self):
        pubsub.Publisher().sendMessage("NEXT")

    def ku_d(self):
        self.presenter.delete()
