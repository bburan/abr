import wx
from datatype import WaveformPoint


class WaveformInteractor(object):

    KEYS = {
        wx.WXK_LEFT:    'left',
        wx.WXK_RIGHT:   'right',
        wx.WXK_DOWN:    'down',
        wx.WXK_UP:      'up',
        43:             'plus',
        45:             'minus',
        61:             'plus',
        390:            'minus',
        388:            'plus',
    }

    def Install(self, presenter, view):
        self.presenter = presenter
        self.view = view
        # Events to capture
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
        if keycode in self.KEYS:
            mname = type + self.KEYS[keycode]
            if hasattr(self, mname):
                getattr(self, mname)(evt)
        elif keycode < 256:
            if chr(keycode) in ['1', '2', '3', '4', '5']:
                mname = type + 'number'
                if hasattr(self, mname):
                    if evt.ShiftDown():
                        polarity = WaveformPoint.VALLEY
                    else:
                        polarity = WaveformPoint.PEAK
                    getattr(self, mname)((polarity, int(chr(keycode))))
            else:
                mname = type + chr(keycode).lower()
                if hasattr(self, mname):
                    getattr(self, mname)()

    def kd_up(self, evt):
        '''
        Move to the prior waveform
        '''
        self.presenter.current += 1

    def kd_down(self, evt):
        '''
        Move to the next waveform
        '''
        self.presenter.current -= 1

    def ku_t(self):
        '''
        Set current waveform as threshold
        '''
        '''
        Set the current waveform as threshold
        '''
        self.presenter.set_threshold()

    def kd_plus(self, evt):
        '''
        Zoom in
        '''
        self.presenter.scale *= 0.9

    def kd_minus(self, evt):
        '''
        Zoom out
        '''
        self.presenter.scale *= 1.1

    def kd_left(self, evt):
        '''
        Move the selected point to the prior best guess.  If shift is pressed,
        move the point in fractional increments instead.
        '''
        if evt.ShiftDown():
            move = ('index', -5)
        else:
            move = ('zc', -1)
        self.presenter.move_selected_point(move)

    def kd_right(self, evt):
        '''
        Move the selected point to the next best guess.  If shift is pressed,
        move the point in fractional increments.
        '''
        if evt.ShiftDown():
            move = ('index', 5)
        else:
            move = ('zc', 1)
        self.presenter.move_selected_point(move)

    def ku_number(self, value):
        '''
        Select the specified point (Peak or Valley), (1-5)
        '''
        self.presenter.toggle = value

    def ku_u(self):
        '''
        Updates guesses for the position of the point for subsequent waveforms
        '''
        self.presenter.update_point()

    def ku_n(self):
        '''
        Toggle between raw and normalized view
        '''
        self.presenter.normalized = not self.presenter.normalized

    def ku_s(self):
        '''
        Save the analysis
        '''
        self.presenter.save()

    def ku_i(self):
        '''
        Make a guess regarding the location of of the valleys
        '''
        self.presenter.guess_n()

    def ku_d(self):
        '''
        Remove the current waveform
        '''
        self.presenter.delete()
