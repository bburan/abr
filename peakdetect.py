import numpy as np
import operator as op

#-------------------------------------------------------------------------------
# Generic clustering algorithms and helper functions
#-------------------------------------------------------------------------------

def nzc_temporal_filtered(fs, waveform, min_spacing=0.3, **kwargs):
    nzc_indices = nzc(waveform)
    p_indices = cluster(nzc_indices, waveform[nzc_indices], 
            min_spacing*1e-3*fs)
    return np.asarray(nzc_indices[p_indices])

def nzc_noise_filtered(fs, waveform, min_noise=None, dev=1.0, min_spacing=0.3,
        **kwargs): 

    if min_noise is None: min_noise = waveform[:1e-3*fs].std()*dev

    p_ind = nzc(waveform)
    n_ind = nzc(-waveform)
    x = np.r_[p_ind, n_ind]
    x.sort()
    #x = np.asarray(sorted(np.r_[np.asarray(p_ind), np.asarray(n_ind)]))

    clusters = cluster_indices(waveform[x], min_noise)
    clusters.pop(0)
    ind = []
    for c in clusters:
        clustered_valleys = [i for i in x[c] if i in n_ind]
        clustered_peaks = [i for i in x[c] if i in p_ind]

        if len(clustered_peaks) > len(clustered_valleys):
            y = waveform[clustered_peaks]
            ind.append(np.where(waveform == y.max())[0][0])

    ind = np.asarray(ind)

    #If too agressive, comment out the following two lines
    if len(ind) > 5:
        f_ind = cluster(ind, waveform[ind], min_spacing*1e-3*fs) 
        ind = ind[f_ind]
    return np.asarray(ind)

def nzc_none(fs, waveform, **kwargs):
    return nzc(waveform)

def bounded_ranges(indices, bounds):
    bounds = zip(bounds[:-1],bounds[1:])
    return [np.where((indices>=b[0])*(indices<b[1]))[0] for b in bounds]

def seed_rank(s, indices, amplitudes, weighting=3, lb=25, ub=50):
    di = np.asarray(indices, dtype='float')-s[0]
    da = np.asarray(amplitudes)-s[1]

    #Filter out peaks outside range
    range_mask = (di >= -lb) * (di <= ub)
    if range_mask.any():
        di = di[range_mask]
        da = da[range_mask]
        indices = np.asarray(indices)[range_mask]
    else:
        return [(s[0], -1)]

    #We give preference to peaks of increasing latency
    neg_mask = di < 0
    di[neg_mask] = di[neg_mask] * 1.5

    #Convert to a ranking
    rankings = zip(indices, abs(di)*1.5 + abs(da))
    rankings.sort(key=op.itemgetter(1))
    return rankings

#-------------------------------------------------------------------------------
# Peak finding algorithms
#-------------------------------------------------------------------------------

def find_np(fs, waveform, nzc='noise_filtered', algorithm='basic', n=5,
        **kwargs): 
    nzcs = globals()['nzc_' + nzc](fs, waveform, **kwargs)
    indices = []
    for n in range(5):
        try:
            p = globals()['np_' + algorithm](fs, waveform, nzcs, n, **kwargs)
            indices.append(p)
        except IndexError:
            indices.append(len(waveform)-1)
    return indices

def np_bound(fs, waveform, indices, n, bounds, bounded_algorithm, **kwargs):
    fun = globals()['np_'+bounded_algorithm]
    range = indices[(indices>=bounds[n])*(indices<bounds[n+1])]
    if len(range) == 1:
        return range[0]
    elif len(range) == 0:
        return bounds[n]
    else:
        return fun(fs, waveform, range, n, **kwargs)
        
def np_basic(fs, waveform, indices, n, min_latency=1.0, **kwargs):
    lb_index = min_latency/1e3*fs
    return indices[indices >= lb_index][n]

def np_none(fs, waveform, indices, n, **kwargs):
    return indices[0][n]

def np_y_fun(fs, waveform, indices, n, fun=max, **kwargs):
    return np.where(waveform == fun(waveform[indices]))[0][0]

def np_seed(fs, waveform, indices, n, seeds, seed_lb=0.25, seed_ub=0.50,
        **kwargs):
    amplitudes = waveform[indices]
    lb = seed_lb*1e-3*fs
    ub = seed_ub*1e-3*fs
    return seed_rank(seeds[n], indices, amplitudes, 3, lb, ub)[0][0]

def manual_np(fs, waveform, start, nzc_algorithm='noise_filtered', **kwargs):
    #points = globals()['nzc_'+nzc_algorithm](fs, waveform)
    points = nzc(waveform)
    dp = abs(points-start)
    i = np.where(dp == dp.min())[0][0]
    di = points[i]-start #Single index steps
    while(1):
        step = (yield (points[i] + di))
        if step is not None:
            if step[0] == 'zc':
                prev = i
                if di < 0:
                    i -= 1
                elif di > 0:
                    i += 1
                i += step[1]
                di = 0
                if i >= len(points) or i < 0:
                    i = prev
            else:
                prev = di
                di += step[1]
                if (points[i] + di) in points:
                    i = np.where(points == (points[i] + di))[0][0]
                    di = 0
                if points[i]+di >= len(waveform) or points[i]+di < 0:
                    di = prev

def manual_np(fs, waveform, start, nzc_algorithm='none', **kwargs):
    points = globals()['nzc_'+nzc_algorithm](fs, waveform)
    dp = abs(points-start)
    i = np.where(dp == dp.min())[0][0]
    di = start-points[i] #Single index steps
    while(1):
        step = (yield (points[i] + di))
        if step is not None:
            if step[0] == 'zc':
                prev = i
                if di < 0 and step[1] > 0: i -= 1
                elif di > 0 and step[1] < 0: i += 1
                i += step[1]
                di = 0
                if i >= len(points) or i < 0:
                    i = prev
            else:
                prev = di
                di += step[1]
                if (points[i] + di) in points:
                    i = np.where(points == (points[i] + di))[0][0]
                    di = 0
                if points[i]+di >= len(waveform) or points[i]+di < 0:
                    di = prev

#-------------------------------------------------------------------------------
# Generic helper functions for above algorithms
#-------------------------------------------------------------------------------

def nzc(x):
    '''Returns indices of all negative zero crossings'''
    dx = np.diff(x,1)
    mask = (dx[1:]<0) & (dx[:-1]>=0)
    return np.where(mask)[0]+1

    dx = x[1:]-x[:-1]
    nzc = [int(i+1) for i in range(len(dx)-1) if dx[i+1]<0 and dx[i]>0]
    return np.array(nzc)

def cluster_indices(x, spacing):
    indices = [0]
    clusters = []
    for i in range(1,len(x)):
        if abs(x[i-1] - x[i]) <= spacing:
            indices.append(i)
        else:
            clusters.append(indices)
            indices = [i]
    clusters.append(indices)
    return clusters

def cluster(x, y, spacing, fun=max):
    clusters = cluster_indices(x, spacing)
    values = []
    for c in clusters:
        index = np.where(y[c] == fun(y[c]))[0][0]
        values.append(c[index])
    return values

if __name__ == '__main__':

    from epl.datafile import loadabr
    from pylab import *
    from numpy import where

    file = 'v:/chamber data/BNB188/ABR-188-4'
    #file = 'c:/desktop/abr/BNB132_ABR-132-4'
    waveforms = loadabr(file, filter=True)
    w = waveforms.get(80)

    subplot(111)
    plot(w.x, w.y)

    n = nzc(w.y)
    p = nzc(w.y)
    plot(w.x[n], w.y[n],'ko')
    plot(w.x[p], w.y[p],'bo')

    peaks = find_np(w.fs, w.y)
    plot(w.x[peaks], w.y[peaks], 'go')
    #n,p = __all_np_clustered(w.fs, w.y)
    #plot(w.x[n], w.y[n],'ro')
    #plot(w.x[p], w.y[p],'go')
    show()
