from pathlib import Path


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


class Dataset:

    filename_template = '{filename}-{frequency}kHz-{user}analyzed.txt'

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

    def find_analyzed_files(self):
        frequency = round(self.frequency * 1e-3, 8)
        filename = self.filename.with_suffix('')
        glob_pattern = self.filename_template.format(filename=filename,
                                                     frequency=frequency,
                                                     user='*')
        path = Path(glob_pattern)
        return list(path.parent.glob(path.name))
