import numpy as np
import operator as op


################################################################################
# Generic clustering algorithms and helper functions
################################################################################
def nzc_temporal_filtered(fs, waveform, min_spacing=0.3):
    nzc_indices = nzc(waveform)
    p_indices = cluster(nzc_indices, waveform[nzc_indices], min_spacing*1e-3*fs)
    return np.asarray(nzc_indices[p_indices])


def nzc_noise_filtered(fs, waveform, dev=1.0, min_spacing=0.3):

    min_noise = waveform[:1e-3*fs].std()*dev

    p_ind = nzc(waveform)
    n_ind = nzc(-waveform)
    x = np.r_[p_ind, n_ind]
    x.sort()

    clusters = cluster_indices(waveform[x], min_noise)
    clusters.pop(0)
    ind = []

    # Eliminate small reversals
    for c in clusters:
        clustered_valleys = [i for i in x[c] if i in n_ind]
        clustered_peaks = [i for i in x[c] if i in p_ind]
        if len(clustered_peaks) > len(clustered_valleys):
            y = waveform[clustered_peaks]
            ind.append(np.where(waveform == y.max())[0][0])
    ind = np.asarray(ind)

    # If algorithm is too agressive, comment out the following two lines
    if len(ind) > 5:
        f_ind = cluster(ind, waveform[ind], min_spacing*1e-3*fs)
        ind = ind[f_ind]
    return np.asarray(ind)


################################################################################
# Peak finding algorithms
################################################################################
def find_np(fs, waveform, nzc_algorithm='noise', guess_algorithm='basic', n=5,
            bounds=None, nzc_algorithm_kw=None, guess_algorithm_kw=None):
    '''
    Estimate the position of peaks in the waveform

    Parameters
    ----------
    fs : float
        sampling frequency of waveform
    waveform : rank-1 ndarray
        the waveform
    nzc_algorithm : string (none, noise, temporal)
        algorithm used to eliminate spurious peaks due to noise in the signal
    guess_algorithm : string (none, basic, seed)
        algorithm used to compute best guess for the peaks
    n : integer
        number of peaks
    nzc_algorithm_kw : dict
        keyword arguments to pass to NZC algorithm
    guess_algorithm_kw : dict
        keyword arguments to pass to guess algorithm
    bounds : list
        ensure that guess for each index falls betweeen the specified bounds
        (see below for additional information)

    Returns
    -------
    List of estimated peak indices

    This algorithm identifies the negative zero crossings (NZCs) of the first
    derivative of the waveform.  These NZCs reflect putative peaks.  For
    particularly noisy signals, there will be many spurious zero crossings due
    to high-frequency artifacts.  Two algorithms are currently available to
    eliminate as many spurious peaks as possible (specified using the
    `nzc_algorithm` argument):

        noise (default)
            Computes the noise floor of the waveform (using the standard
            deviation of the first msec of the signal) and groups together any
            sequence of NZCs whose amplitude is within `dev` standard deviations
            of each other.  The indices of the NZC with the maximum amplitude in
            each cluster is returned.  Takes dev as a keyword argument
            indicating the number of standard deviations (from noise floor) to
            use as the threshold for clustering NZC sequences.

        temporal
            Groups together all sequences of NZCs that occur within
            `min_spacing` (in seconds) of each other.  Returns the indices of
            the NZC with the maximum amplitude in each cluster.

    Note that you may specify None to indicate you do not wish spurious zero
    crossings to be eliminated.  Once a list of indices for putative peaks are
    identified, the list can be further processed to identify which of these
    peaks are the most likely ones of interest (specified using the
    `guess_algorithm` argument).

        None
            Just return the first n indices
        basic
            Return the first n indices after `min_latency` (in msec)
        seed
            Weights the putative peaks in terms of their proximy to a list of
            `seeds` in the format [(index_1, amplitude_1), (index_2,
            amplitude_2), ... (index_n, amplitude_n)].  The highest-rated
            match for each seed is returned.

    If a list of bounds are specified, this will be used to winnow down the list
    of putative peaks that will be provided to the guess_algorithm.  The
    `Bounds` must be a list of length `n`+1.  The first index must fall between
    bounds[0] and bounds[1].  The nth index must fall between bounds[n] and
    bounds[n+1].
    '''

    # Get the NZC indices (e.g. the putative guess for the peak indices)
    if nzc_algorithm_kw is None:
        nzc_algorithm_kw = {}
    if nzc_algorithm is None:
        nzc_indices = nzc(waveform)
    else:
        nzc_func = globals()['nzc_%s_filtered' % nzc_algorithm]
        nzc_indices = nzc_func(fs, waveform, **nzc_algorithm_kw)

    indices = []
    guess_func = globals()['np_%s' % guess_algorithm]
    if guess_algorithm_kw is None:
        guess_algorithm_kw = {}

    if bounds is not None:
        for p in range(n):
            mask = (nzc_indices > bounds[p]) & (nzc_indices < bounds[p+1])
            bounded_indices = nzc_indices[mask]
            # If only one NZC falls within the bound, use that as the guess
            if len(bounded_indices) == 1:
                indices.append(bounded_indices[0])
            # If no NZCs fall within the bound, use the lower end of the bounded
            # range as the guess
            elif len(bounded_indices) == 0:
                indices.append(bounds[p])
            else:
                try:
                    # If the algorithm cannot make a guess as to the best index,
                    # it will raise an IndexError.  We capture that and place
                    # the index on the very end of the waveform.
                    guess = guess_func(fs, waveform, bounded_indices, p,
                                       **guess_algorithm_kw)
                    indices.append(guess)
                except IndexError:
                    indices.append(len(waveform)-1)
    else:
        for p in range(n):
            try:
                guess = guess_func(fs, waveform, nzc_indices, p,
                                   **guess_algorithm_kw)
                indices.append(guess)
            except IndexError:
                indices.append(len(waveform)-1)
    return indices


def np_none(fs, waveform, indices, n):
    '''
    Returns the first n indices
    '''
    return indices[0][n]


def np_basic(fs, waveform, indices, n, min_latency=1.0):
    '''
    Returns the first n indices whose latency is greater than min_latency
    '''
    lb_index = min_latency/1e3*fs
    return indices[indices >= lb_index][n]


def np_y_fun(fs, waveform, indices, n, fun=max):
    return np.where(waveform == fun(waveform[indices]))[0][0]


def np_seed(fs, waveform, indices, n, seeds, seed_lb=0.25, seed_ub=0.50):
    amplitudes = waveform[indices]
    lb = seed_lb*1e-3*fs
    ub = seed_ub*1e-3*fs
    return seed_rank(seeds[n], indices, amplitudes, 3, lb, ub)[0][0]


def iterator_np(fs, waveform, start, nzc_filter=None):
    '''
    Coroutine that steps through the possible guesses for the peak
    '''
    if nzc_filter is None:
        nzc_indices = nzc(waveform)
    else:
        nzc_indices = globals()['nzc_'+nzc_filter](fs, waveform)

    dp = abs(nzc_indices-start)
    i = np.where(dp == dp.min())[0][0]
    di = start-nzc_indices[i]  # Single index steps

    while True:
        step = (yield (nzc_indices[i] + di))
        if step is not None:
            if step[0] == 'zc':
                prev = i
                if di < 0 and step[1] > 0:
                    i -= 1
                elif di > 0 and step[1] < 0:
                    i += 1
                i += step[1]
                di = 0
                if i >= len(nzc_indices) or i < 0:
                    i = prev
            else:
                prev = di
                di += step[1]
                if (nzc_indices[i] + di) in nzc_indices:
                    i = np.where(nzc_indices == (nzc_indices[i] + di))[0][0]
                    di = 0
                if nzc_indices[i]+di >= len(waveform) or nzc_indices[i]+di < 0:
                    di = prev


################################################################################
# Generic helper functions for above algorithms
################################################################################
def nzc(x):
    '''
    Returns indices of the negative zero crossings of the first derivative of x
    '''
    dx = np.diff(x, 1)
    mask = (dx[1:] < 0) & (dx[:-1] >= 0)
    return np.where(mask)[0]+1


def cluster_indices(x, distance):
    '''
    Group together indices within `distance` of each other
    '''
    indices = [0]
    clusters = []
    for i in range(1, len(x)):
        if abs(x[i-1] - x[i]) <= distance:
            indices.append(i)
        else:
            clusters.append(indices)
            indices = [i]
    clusters.append(indices)
    return clusters


def cluster(indices, y, distance, fun=max):
    clusters = cluster_indices(indices, distance)
    values = []
    for c in clusters:
        index = np.where(y[c] == fun(y[c]))[0][0]
        values.append(c[index])
    return values


def seed_rank(s, indices, amplitudes, weighting=3, lb=25, ub=50):
    di = np.asarray(indices, dtype='float')-s[0]
    da = np.asarray(amplitudes)-s[1]

    # Filter out peaks outside range
    range_mask = (di >= -lb) * (di <= ub)
    if range_mask.any():
        di = di[range_mask]
        da = da[range_mask]
        indices = np.asarray(indices)[range_mask]
    else:
        return [(s[0], -1)]

    # We give preference to peaks of increasing latency
    neg_mask = di < 0
    di[neg_mask] = di[neg_mask] * 1.5

    # Convert to a ranking
    rankings = zip(indices, abs(di)*1.5 + abs(da))
    rankings.sort(key=op.itemgetter(1))
    return rankings
