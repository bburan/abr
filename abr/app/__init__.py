def add_default_arguments(parser):
    parser.add_argument('--nofilter', action='store_false', dest='filter',
                        default=True, help='Do not filter waveform')
    parser.add_argument('--lowpass', action='store', dest='lowpass',
                        help='Lowpass cutoff (Hz), default 10,000 Hz',
                        default=10e3, type=float)
    parser.add_argument('--highpass', action='store', dest='highpass',
                        help='Highpass cutoff (Hz), default 200 Hz',
                        default=200, type=float)
    parser.add_argument('--order', action='store', dest='order',
                        help='Filter order, default 1st order', default=1,
                        type=int)
