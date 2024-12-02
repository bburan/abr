import functools
from pathlib import Path
import re


P_RATER = re.compile('.*(?:kHz|click)(?:-(\w+))?-analyzed.txt')


def get_rater(filename):
    try:
        return P_RATER.match(filename.name).group(1)
    except:
        return 'Unknown'


class DataCollection:

    def __init__(self, filename):
        self.filename = Path(filename)

    @property
    def fs(self):
        raise NotImplementedError

    @property
    def data(self):
        raise NotImplementedError

    @property
    def frequencies(self):
        raise NotImplementedError

    @property
    def name(self):
        raise NotImplementedError

    def iter_frequencies(self):
        raise NotImplementedError


@functools.total_ordering
class Dataset:

    filename_template = '{filename}-{frequency}-{rater}analyzed.txt'

    def __init__(self, parent, frequency):
        self.parent = parent
        self.frequency = frequency

    @property
    def filename(self):
        return self.parent.filename

    @property
    def fs(self):
        return self.parent.fs

    def get_series(self, filter_settings=None):
        raise NotImplementedError

    def get_analyzed_filename(self, rater):
        if self.frequency == -1:
            frequency = 'click'
        else:
            frequency = round(self.frequency * 1e-3, 8)
            frequency = f'{frequency}kHz'

        filename = self.filename.with_suffix('')
        if rater != '*':
            rater = rater + '-'
        return self.filename_template \
            .format(filename=filename, frequency=frequency, rater=rater)

    def find_analyzed_files(self):
        glob_pattern = self.get_analyzed_filename('*')
        path = Path(glob_pattern)
        return list(path.parent.glob(path.name))

    def list_raters(self):
        return [get_rater(filename) for filename in self.find_analyzed_files()]

    def load_analysis(self, rater):
        from . import load_analysis
        r = load_analysis(self.get_analyzed_filename(rater))
        print(r)
        return r

    def __lt__(self, other):
        if not isinstance(other, Dataset):
            raise NotImplemented
        return (self.filename, self.frequency) < \
            (other.filename, other.frequency)

    def __eq__(self, other):
        if not isinstance(other, Dataset):
            raise NotImplemented
        return (self.filename, self.frequency) == \
            (other.filename, other.frequency)

    def __hash__(self):
        return hash((self.filename, self.frequency))
