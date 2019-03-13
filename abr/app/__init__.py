from abr.parsers import Parser

from scipy import stats


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
    parser.add_argument('--parser', default='HDF5', help='Parser to use')
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
