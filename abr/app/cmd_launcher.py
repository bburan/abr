
import enaml
from enaml.qt.qt_application import QtApplication

with enaml.imports():
    from abr.launch_window import LaunchWindow


def main():
    app = QtApplication()
    window = LaunchWindow()
    window.show()
    app.start()
    app.stop()
