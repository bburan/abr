def add_default_arguments(parser):
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
    parser.add_argument('--n-waves', help='Number of waves to analyze', default=5, type=int)
    parser.add_argument('--user', help='Name of person analyzing data')
    parser.add_argument('--parser', default='HDF5', help='Parser to use')
