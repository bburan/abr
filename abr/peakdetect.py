import operator as op

import numpy as np
import pandas as pd
from scipy import signal, stats


def find_peaks(waveform, distance=0.5e-3, prominence=50, wlen=None,
               invert=False, detrend=True):

    y = -waveform.y if invert else waveform.y
    if detrend:
        y = signal.detrend(y)
    x = waveform.x
    fs = waveform.fs
    prominence = np.percentile(y, prominence)
    i_distance = round(fs*distance)
    if wlen is not None:
        wlen = round(fs*wlen)
    kwargs = {'distance': i_distance, 'prominence': prominence, 'wlen': wlen}
    indices, metrics = signal.find_peaks(y, **kwargs)

    metrics.pop('left_bases')
    metrics.pop('right_bases')
    metrics['x'] = waveform.x[indices]
    metrics['y'] = waveform.y[indices]
    metrics['index'] = indices
    metrics = pd.DataFrame(metrics)
    return metrics


def guess_peaks(metrics, latency):
    p_score_norm = metrics['prominences'] / metrics['prominences'].sum()
    guess = {}
    for i in sorted(latency.keys()):
        l = latency[i]
        l_score = metrics['x'].apply(l.pdf)
        l_score_norm = l_score / l_score.sum()
        score = 5 * l_score_norm + p_score_norm
        m = score.idxmax()
        if np.isfinite(m):
            guess[i] = metrics.loc[m]
            metrics = metrics.loc[m+1:]
        else:
            guess[i] = {'x': l.mean(), 'y': 0}

    return pd.DataFrame(guess).T


def generate_latencies_bound(guess, max_time=8.5, sd=0.25):
    latency = {}
    waves = sorted(guess.index.values)
    for lb, ub in zip(waves[:-1], waves[1:]):
        t_lb = guess.loc[lb, 'x']
        t_ub = guess.loc[ub, 'x']
        b = (t_ub-t_lb)/sd
        latency[lb] = stats.truncnorm(0, b, t_lb, sd)

    g = guess.iloc[-1]
    t = g['x']
    wave = g.name
    b = (max_time-t)/sd
    latency[wave] = stats.truncnorm(0, b, t, sd)
    return latency


def generate_latencies_skewnorm(guess, skew=3):
    latencies = {}
    for w, row in guess.iterrows():
        latencies[w] = stats.skewnorm(skew, row['x'], 0.1)
    return latencies


def guess_iter(waveforms, latencies, invert=False):
    waveforms = sorted(waveforms, key=op.attrgetter('level'), reverse=True)
    guesses = {}
    for w in waveforms:
        metrics = find_peaks(w, invert=invert)
        guesses[w.level] = guess_peaks(metrics, latencies)
        latencies = generate_latencies_skewnorm(guesses[w.level])
    return guesses


def guess(waveforms, latencies, invert=False):
    guesses = {}
    for w in waveforms:
        metrics = find_peaks(w, invert=invert)
        guesses[w.level] = guess_peaks(metrics, latencies[w.level])
    return guesses


def peak_iterator(waveform, index, invert=False):
    '''
    Coroutine that steps through the possible guesses for the peak

    Parameters
    ----------
    index : tuple of (step_mode, step_size)
    '''
    metrics = find_peaks(waveform, distance=0.25e-3, prominence=25,
                         invert=invert)

    while True:
        step_mode, step_size = yield index
        if step_mode == 'zero_crossing':
            try:
                delta = metrics['index'] - index
                if step_size == 1:
                    i = delta[delta > 0].idxmin()
                    index = metrics.loc[i, 'index']
                elif step_size == -1:
                    i = delta[delta < 0].idxmax()
                    index = metrics.loc[i, 'index']
            except:
                pass
        elif step_mode == 'time':
            # Ensure step size is at least one period in length
            step_size = max(abs(step_size), 1/waveform.fs) * np.sign(step_size)
            index += round(step_size * waveform.fs)
        elif step_mode == 'set':
            index = step_size
        index = int(round(np.clip(index, 0, len(waveform.x)-1)))
