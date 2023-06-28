from functools import cached_property, lru_cache
import glob
import json
import os.path
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

from abr.datatype import ABRWaveform, ABRSeries

from .dataset import DataCollection, Dataset


def get_filename(pathname, suffix='ABR average waveforms.csv'):
    if pathname.is_file():
        if pathname.name.endswith(suffix):
            return pathname
        else:
            raise IOError('Invalid ABR file')
    filename = pathname / suffix
    if filename.exists():
        return filename
    filename = pathname / f'{pathname.stem} {suffix}'
    if filename.exists():
        return filename
    raise IOError(f'Could not find average waveforms file for {pathname}')


@lru_cache(maxsize=64)
def read_file(filename):
    with filename.open() as fh:
        # This supports a variable-length header where we may not have included
        # some levels (e.g., epoch_n and epoch_reject_ratio).
        header = {}
        while True:
            line = fh.readline()
            if line.startswith('time'):
                break
            name, *keys = line.split(',')
            header[name] = np.array(keys).astype('f')
        data = pd.read_csv(fh, index_col=0, header=None)

    header = pd.MultiIndex.from_arrays(list(header.values()),
                                       names=list(header.keys()))
    data.index.name = 'time'
    data.index *= 1e3
    data.columns = header
    return data.T


class PSIDataCollection(DataCollection):

    def __init__(self, filename):
        filename = Path(filename)
        self.filename = get_filename(filename)

    @cached_property
    def fs(self):
        settings_file = get_filename(self.filename.parent, 'ABR processing settings.json')
        if settings_file.exists():
            fs = json.loads(settings_file.read_text())['actual_fs']
        else:
            fs = np.mean(np.diff(data.columns.values)**-1)
        return fs

    @cached_property
    def data(self):
        data = read_file(self.filename)
        keep = ['frequency', 'level']
        drop = [c for c in data.index.names if c not in keep]
        return data.reset_index(drop, drop=True)

    @cached_property
    def frequencies(self):
        return self.data.index.unique('frequency').values

    @property
    def name(self):
        return self.filename.parent.stem

    def iter_frequencies(self):
        for frequency in self.frequencies:
            yield PSIDataset(self, frequency)


class PSIDataset(Dataset):

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
        data = self.parent.data.loc[self.frequency]
        if filter_settings is not None:
            Wn = filter_settings['highpass'], filter_settings['lowpass']
            N = filter_settings['order']
            b, a = signal.iirfilter(N, Wn, fs=self.fs)
            data_filt = signal.filtfilt(b, a, data.values, axis=-1)
            data = pd.DataFrame(data_filt, columns=data.columns, index=data.index)

        waveforms = []
        for level, w in data.iterrows():
            level = float(level)
            waveforms.append(ABRWaveform(self.fs, w, level))

        series = ABRSeries(waveforms, self.frequency)
        series.filename = self.parent.filename
        series.id = self.parent.filename.parent.name
        return series


def iter_all(path):
    results = []
    path = Path(path)
    if path.stem.endswith('abr_io'):
        yield from PSIDataCollection(path).iter_frequencies()
    else:
        for subpath in path.glob('**/*abr_io'):
            yield from PSIDataCollection(subpath).iter_frequencies()
