import argparse

import enaml
from enaml.application import deferred_call
from enaml.qt.qt_application import QtApplication
from scipy import stats

with enaml.imports():
    from abr.launch_window import LaunchWindow, STORE
    from abr.main_window import (DNDWindow, load_files, SerialWindow)
    from abr.compare_window import CompareWindow
    from abr.presenter import SerialWaveformPresenter, WaveformPresenter


from abr.compare import Compare
from abr.parsers import Parser


P_LATENCIES = {
    1: stats.norm(1.5, 0.5),
    2: stats.norm(2.5, 1),
    3: stats.norm(3.0, 1),
    4: stats.norm(4.0, 1),
    5: stats.norm(5.0, 2),
}


def add_default_arguments(parser, waves=True):
    parser.add_argument('--nofilter', action='store_false', dest='filter',
                        default=True, help='Do not filter waveform')
    parser.add_argument('--lowpass',
                        help='Lowpass cutoff (Hz), default 3000 Hz',
                        default=3000, type=float)
    parser.add_argument('--highpass',
                        help='Highpass cutoff (Hz), default 300 Hz',
                        default=300, type=float)
    parser.add_argument('--order',
                        help='Filter order, default 1st order', default=1,
                        type=int)
    parser.add_argument('--parser', default='EPL', help='Parser to use')
    parser.add_argument('--user', help='Name of person analyzing data')
    if waves:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--threshold-only', action='store_true')
        group.add_argument('--all-waves', action='store_true')
        group.add_argument('--waves', type=int, nargs='+')


def parse_args(parser, waves=True):
    options = parser.parse_args()
    exclude = ('filter', 'lowpass', 'highpass', 'order', 'parser', 'user',
               'waves', 'all_waves', 'threshold_only')
    new_options = {k: v for k, v in vars(options).items() if k not in exclude}
    filter_settings = None
    if options.filter:
        filter_settings = {
            'lowpass': options.lowpass,
            'highpass': options.highpass,
            'order': options.order,
        }
    new_options['parser'] = Parser(options.parser, filter_settings,
                                   options.user)

    if not waves:
        return new_options

    if options.all_waves:
        waves = [1, 2, 3, 4, 5]
    elif options.threshold_only:
        waves = []
    else:
        waves = options.waves[:]
    new_options['latencies'] = {w: P_LATENCIES[w] for w in waves}
    return new_options


def main():
    parser = argparse.ArgumentParser('abr')
    parser.add_argument('--clear-settings', action='store_true',
                        help='Clear persisted settings')
    args = parser.parse_args()
    if args.clear_settings:
        STORE.clear()

    app = QtApplication()
    window = LaunchWindow()
    window.show()
    app.start()
    app.stop()


def main_gui():
    parser = argparse.ArgumentParser('abr-gui')
    add_default_arguments(parser)
    parser.add_argument('--demo', action='store_true', dest='demo',
                        default=False, help='Load demo data')
    parser.add_argument('filenames', nargs='*')
    options = parse_args(parser)

    app = QtApplication()
    view = DNDWindow(parser=options['parser'], latencies=options['latencies'])
    deferred_call(load_files, options['parser'], options['latencies'],
                  options['filenames'], view.find('dock_area'))

    view.show()
    app.start()
    app.stop()


def main_batch():
    parser = argparse.ArgumentParser('abr-batch')
    add_default_arguments(parser)
    parser.add_argument('dirnames', nargs='*')
    parser.add_argument('--skip-errors', action='store_true')
    options = parse_args(parser)
    parser = options['parser']

    app = QtApplication()
    presenter = SerialWaveformPresenter(parser=parser,
                                        latencies=options['latencies'],
                                        paths=options['dirnames'])
    view = SerialWindow(presenter=presenter)
    view.show()
    app.start()
    app.stop()


def main_compare():
    parser = argparse.ArgumentParser("abr-compare")
    add_default_arguments(parser)
    parser.add_argument('directory')
    options = parse_args(parser)

    presenter_a = WaveformPresenter(latencies=options['latencies'], parser=options['parser'], interactive=False)
    presenter_b = WaveformPresenter(latencies=options['latencies'], parser=options['parser'], interactive=False)
    presenter_c = WaveformPresenter(latencies=options['latencies'], parser=options['parser'])

    app = QtApplication()
    compare = Compare(options['parser'], options['directory'])
    view = CompareWindow(compare=compare,
                         rater=options['parser']._user,
                         presenter_a=presenter_a,
                         presenter_b=presenter_b,
                         presenter_c=presenter_c,
                         )
    view.show()
    app.start()
    app.stop()
