#!/usr/bin/env python

from __future__ import division

from collections import (
    Counter,
    defaultdict,
    OrderedDict,
)
import operator
import os

from six import string_types

import numpy as np
from scipy import stats
from munkres import Munkres


def parameterized_feature_coefficient(fn):
    def batch_similarity(params, a, bs):
        return np.array([fn(params, a, b) for b in bs])

    def similarity_matrix(params, as_, bs):
        return np.array([fn.batch_similarity(params, a, bs) for a in as_])

    def stream_batch_similarities(params, as_, bs):
        for a in as_:
            yield fn.batch_similarity(params, a, bs)

    def stream_similarities(params, as_, bs):
        batches = fn.stream_batch_similarities(params, as_, bs)
        for batch in batches:
            for score in batch:
                yield score

    def override_batch_similarity(bulk_fn):
        setattr(fn, 'batch_similarity', bulk_fn)
        return bulk_fn

    def override_similarity_matrix(matrix_fn):
        setattr(fn, 'similarity_matrix', matrix_fn)
        return matrix_fn

    override_batch_similarity(batch_similarity)
    override_similarity_matrix(similarity_matrix)

    setattr(fn, 'override_batch_similarity', override_batch_similarity)
    setattr(fn, 'override_similarity_matrix', override_similarity_matrix)
    setattr(fn, 'stream_batch_similarities', stream_batch_similarities)
    setattr(fn, 'stream_similarities', stream_similarities)

    return fn


@parameterized_feature_coefficient
def reference_cutoff_tanimoto_similarity(cutoffs, a, b):
    total = 0  # $all -> total
    comm = 0
    for i, (ax, bx) in enumerate(zip(a,b)):
        if ax != 0 or bx != 0:
            total += 1
            if ax - bx >= 0 and ax - bx <= cutoffs[i]:
                comm += 1
            elif ax - bx < 0 and bx - ax <= cutoffs[i]:
                comm +=1
    if total == 0:
        return 0.
    else:
        return comm / (total * 2 - comm)


@parameterized_feature_coefficient
def adjusted_reference_cutoff_tanimoto_similarity(cutoffs, a, b):
    N = len(a)
    total = 0
    comm = 0
    for i, (ax, bx) in enumerate(zip(a,b)):
        if ax != 0 or bx != 0:
            total += 1
            delta = ax - bx
            if delta >= 0 and delta <= cutoffs[i]:
                comm += 1
            elif delta < 0 and -delta <= cutoffs[i]:
                comm +=1
    if total == 0:
        return 0.
    else:
        return comm / total


@parameterized_feature_coefficient
def cutoff_tanimoto_similarity(cutoffs, a, b):
    """ Compute the PocketFEATURE tanimoto similarity of two FEATURE vectors
        This method takes two vectors and treats each pair of elments matched
        they differ by less than the supplied cutoff for that index.
        The number matched elements is then divided by the total number of
        elements "present" (e.g. non-zero) and this value returned as 
        the score.
        If zeroed is false, the elements also need the same sign.
    """
    union = np.logical_or(a != 0, b != 0)
    union_size = np.count_nonzero(union)
    shared = union
    if union_size > 0:
        delta = np.abs(a[shared] - b[shared])
        intersection = delta < cutoffs[shared]
        intersection_size = np.count_nonzero(intersection)
        return intersection_size / union_size
    else:
        return 0.


@cutoff_tanimoto_similarity.override_batch_similarity
def bulk_cutoff_tanimoto_similarity(cutoffs, a, bs):
    n = len(bs)
    unions = np.logical_or(a !=0, bs != 0)
    a_repeat = np.repeat(a[np.newaxis], n, axis=0)
    cutoffs_repeat = np.repeat(cutoffs[np.newaxis], n, axis=0)
    in_bounds = np.abs(a_repeat - bs) < cutoffs_repeat
    intersections = np.logical_and(unions, in_bounds)
    union_sizes = unions.sum(axis=1)
    intersection_sizes = intersections.sum(axis=1)
    old_error_settings = np.seterr(divide='ignore')
    scores = intersection_sizes / union_sizes
    scores[~np.isfinite(scores)] = 0.
    np.seterr(**old_error_settings)
    return scores


@parameterized_feature_coefficient
def cutoff_tversky22_similarity(cutoffs, a, b):
    """ Compute the PocketFEATURE tanimoto similarity of two FEATURE vectors
        This method takes two vectors and treats each pair of elements matched
        they differ by less than the supplied cutoff for that index.
        The number matched elements is then divided by the total number of
        elements "present" (e.g. non-zero) and this value returned as 
        the score.
        If zeroed is false, the elements also need the same sign.
    """
    union = np.logical_or(a != 0, b != 0)
    union_size = np.count_nonzero(union)
    shared = union
    if union_size > 0:
        delta = np.abs(a[shared] - b[shared])
        intersection = delta < cutoffs[shared]
        intersection_size = np.count_nonzero(intersection)
        return intersection_size / (2 * union_size - intersection_size)
    else:
        return 0.


@cutoff_tversky22_similarity.override_batch_similarity
def bulk_cutoff_tversky22_similarity(cutoffs, a, bs):
    n = len(bs)
    unions = np.logical_or(a !=0, bs != 0)
    a_repeat = np.repeat(a[np.newaxis], n, axis=0)
    cutoffs_repeat = np.repeat(cutoffs[np.newaxis], n, axis=0)
    in_bounds = np.abs(a_repeat - bs) < cutoffs_repeat
    intersections = np.logical_and(unions, in_bounds)
    union_sizes = unions.sum(axis=1)
    intersection_sizes = intersections.sum(axis=1)
    old_error_settings = np.seterr(divide='ignore')
    scores = intersection_sizes / (2. * union_sizes - intersection_sizes)
    scores[~np.isfinite(scores)] = 0.
    np.seterr(**old_error_settings)
    return scores


@parameterized_feature_coefficient
def cutoff_dice_similarity(cutoffs, a, b):
    """ Compute the PocketFEATURE tanimoto similarity of two FEATURE vectors
        This method takes two vectors and treats each pair of elments matched
        they differ by less than the supplied cutoff for that index.
        The number matched elements is then divided by the total number of
        elements "present" (e.g. non-zero) and this value returned as 
        the score.
        If zeroed is false, the elements also need the same sign.
    """
    union = np.logical_or(a != 0, b != 0)
    union_size = np.count_nonzero(union)
    shared = union
    if union_size > 0:
        delta = np.abs(a[shared] - b[shared])
        intersection = delta < cutoffs[shared]
        intersection_size = np.count_nonzero(intersection)
        return (2.0 * intersection_size) / (union_size - intersection_size)
    else:
        return 0.


@cutoff_dice_similarity.override_batch_similarity
def bulk_cutoff_dice_similarity(cutoffs, a, bs):
    n = len(bs)
    unions = np.logical_or(a !=0, bs != 0)
    a_repeat = np.repeat(a[np.newaxis], n, axis=0)
    cutoffs_repeat = np.repeat(cutoffs[np.newaxis], n, axis=0)
    in_bounds = np.abs(a_repeat - bs) < cutoffs_repeat
    intersections = np.logical_and(unions, in_bounds)
    union_sizes = unions.sum(axis=1)
    intersection_sizes = intersections.sum(axis=1)
    old_error_settings = np.seterr(divide='ignore')
    scores = (2.0 * intersection_sizes) / (union_sizes - intersection_sizes)
    scores[~np.isfinite(scores)] = 0.
    np.seterr(**old_error_settings)
    return scores


def normalize_score(score, mode):
    return 2 / (1 + (score / mode) ** 2) - 1


def scale_score_none(params, sizes, score):
    return score


def scale_score_to_alignment_tanimoto(params, sizes, score):
    nA, nB, nP, nAlign = sizes
    coeff = nAlign / (nA + nB - nAlign)
    rescaled = coeff * score
    return rescaled


def scale_score_to_alignment_evalue(params, sizes, score):
    nA, nB, nP, nAlign = sizes
    if nAlign == 0 or score == 0:
        return 0.
    if len(params) >= 2:
        l, k = params[:2]
    else:
        l, k = 5, 10
    scale = k * (nA * nB) / nAlign ** 2
    exp = np.exp(l * score)
    return scale * exp


def nonlinear_fit(x, m, p, b):
    return m * x ** p + b


def scale_score_fitted_zscore(params, sizes, score):
    nA, nB, nP, nAlign = sizes
    muM, muP, muB, sigM, sigP, sigB = params
    mu =  nonlinear_fit(score, muM, muP, muB)
    sigma = nonlinear_fit(score, sigM, sigP, sigB)
    z_score = (score - mu) / sigma
    return z_score


def scale_score_fitted_evd(params, sizes, score):
    z_params = params[:6]
    evd_params = params[6:]
    dist = stats.gumbel_r(*evd_params)
    z_score = scale_score_fitted_zscore(z_params, sizes, score)
    pvalue = dist.pdf(z_score)
    return pvalue


def unique_product(p, q, skip=0):
    for i, x in enumerate(p, start=skip):
        for y in q[i:]:
            yield x,y


def filter_scores(scores, cutoff, wrapper=None):
    wrapper = wrapper or (lambda x: x)
    filtered = ((k, v) for k, v in scores.items() if v <= cutoff)
    return wrapper(filtered)


#def munkres(costs, maximize=False):
#    N, M = costs.shape
#
#    # Ensure we have at least as many columns as we do rows
#    # Transpose if needed
#    if M < N:
#        costs = costs.transpose()
#        N, M = M, N
#
#    # If maximizing, convert to a minimization problem by
#    # subtracting off the largest overall value from all values
#    if maximize:
#        costs_0 = costs.max() * np.ones(costs.shape) - costs
#    else:
#        costs_0 = np.array(costs)
#
#    # Subtract off the smallest value in each row
#    min_per_row_0 = costs_0.min(axis=1)
#    delta_0 = np.tile(min_per_row_0, (M, 1)).transpose()
#    costs_1 = costs_0 - delta_0
#
#    # Subtract off the smallest value in each column
#    min_per_col_1 = costs_1.min(axis=0)
#    delta_1 = np.tile(min_per_col, (N, 1))
#    costs_2 = costs_1 - delta_1
#
#    # Calculate which elements can be assigned
#    #assignable_2 =
#    uniq_per_col = np.sum(zero_in, axis=0)


def greedy_align(scores, maximize=False):
    """ Given a MatrixValue object, elements in one set are
        aligned with the best unaligned element in the other set
        until none remain
    """
    # Takes a MatrixValue object instead of an array for now
    accepted = []
    chosen_keys = defaultdict(set)
    ordered_items = sorted(scores.items(), key=operator.itemgetter(1), reverse=maximize)
    for keys, value in ordered_items:
        # Make sure we only check that a key has been chosen from a given item
        indexed_keys = list(enumerate(keys))
        if all(key not in chosen_keys[idx] for idx, key in indexed_keys):
            for idx, key in indexed_keys:
                chosen_keys[idx].add(key)
            accepted.append((keys, value))
    return accepted


def only_best_align(scores, maximize=False):
    # Determine functions/defaults
    if maximize:
        default = None, -np.inf
        is_better = operator.gt
    else:
        default = None, np.inf
        is_better = operator.lt

    best_scoresA = OrderedDict()
    best_scoresB = OrderedDict()

    # Find the best score for each point in the alignment
    for (keyA, keyB), score in scores.items():
        best_keyA, best_scoreA = best_scoresA.get(keyA, default)
        best_keyB, best_scoreB = best_scoresB.get(keyB, default)
        if is_better(score, best_scoreA):
            best_scoresA[keyA] = keyB, score
        if is_better(score, best_scoreB):
            best_scoresB[keyB] = keyA, score

    # Select only those pairs where the best is mutual
    accepted = []
    for keyA, (keyB, score) in best_scoresA.items():
        best_keyB, scoreB = best_scoresB.get(keyB, default)
        if best_keyB is None:
            continue
        elif best_keyB == keyA:
            accepted.append(((keyA, keyB), score))

    # Order the aligned points by score
    prioritized = sorted(accepted, key=operator.itemgetter(1), reverse=maximize)

    return prioritized


def munkres_align(scores, shift_negative=False, maximize=False):
    munkres_process = Munkres()
    lowest = min(map(min, scores)) if shift_negative else None
    highest = max(map(max, scores)) if maximize else None

    # Various cost matrix manipulations that can be enabled
    # Probably faster to do in numpy before calling
    if lowest is not None and highest is not None:
        make_score = lambda cost: (highest - cost) - lowest
        costs = munkres_process.make_cost_matrix(scores, make_score)
    elif lowest:
        make_score = lambda cost: cost - lowest
        costs = munkres_process.make_cost_matrix(scores, make_score)
    elif highest:
        make_score = lambda cost: highest - cost
        costs = munkres_process.make_cost_matrix(scores, make_score)
    else:
        costs = scores
   
    indexes = munkres_process.compute(costs)
    return indexes


class GaussianStats(object):
    """ A class for calculating simple statistics over streams of data """

    def __init__(self, n=0, mean=None, m2=None, mins=None, maxes=None, mode_bins=None,
                 mode_binning=None, store=None, store_formatter="{0:0.3f}\n".format):
        if isinstance(mode_binning, int):
            self._bin_for_mode = lambda x: round(x, mode_binning)
        else:
            self._bin_for_mode = mode_binning
        self._store_dest = store
        self.reset(n=n, mean=mean, m2=m2, mins=mins, maxes=maxes, mode_bins=mode_bins)
        if isinstance(store_formatter, string_types):
            self._store_formatter = store_formatter.format
        else:
            self._store_formatter = store_formatter

    def reset(self, n=0, mean=None, m2=None, mins=None, maxes=None, mode_bins=None):
        if mean is None:
            mean = np.zeros(1)
        if m2 is None:
            m2 = np.zeros(1)
        if mins is None:
            mins = np.zeros(1)
        if maxes is None:
            maxes = np.zeros(1)
        if self._bin_for_mode is not None:
            if mode_bins is None:
                mode_bins = Counter()

        self._n = n
        self._mean = np.array(mean)
        self._m2 = np.array(m2)
        self._mins = np.array(mins)
        self._maxes = np.array(maxes)
        self._mode_counts = mode_bins

    def record(self, item):
        sample = np.array(item)

        n = self.n + 1
        delta = sample - self._mean
        mean = self._mean + delta / n
        m2 = self._m2 + delta * (sample - mean)
        mins = np.minimum(self._mins, sample)
        maxes = np.maximum(self._maxes, sample)

        if self._mode_counts is not None:
            bin = self._bin_for_mode(item)
            self._mode_counts[bin] += 1

        self._n = n
        self._mean = mean
        self._m2 = m2
        self._mins = mins
        self._maxes = maxes

        self.store(item)

        return item

    def merge(self, other):
        """
        Take two OnlineStatistics-like objects and produce a third
        From: https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Parallel_algorithm
        """
        n = self.n + other.n
        mean = (self.n * self.mean + other.n * other.mean) / n

        delta = other.mean - self.mean
        scaled_delta = delta**2 * ((self.n * other.n) / n)

        m2 = self.m2 + other.m2 + scaled_delta

        mins = np.minimum(self.mins, other.mins)
        maxes = np.maximum(self.maxes, other.maxes)

        #TODO: Add mode merging

        cls = type(self)
        return cls(n=n, mean=mean, m2=m2, mins=mins, maxes=maxes)

    def store(self, item):
        if self._store_dest is not None:
            if self._store_formatter is not None:
                entry = self._store_formatter(item)
            else:
                entry = item
            self._store_dest.write(entry)

    def get_top_n_modes(self, n):
        if self._mode_counts is not None:
            modes = self._mode_counts.most_common(n)
            if len(modes) > 0:
                return modes
        return None

    @property
    def n(self):
        return self._n

    @property
    def mean(self):
        return self._mean

    @property
    def m2(self):
        return self._m2

    @property
    def variance(self):
        if self.n < 2:
            return np.zeros(self.m2.shape)
        else:
            return self.m2 / (self.n - 1)

    @property
    def std_dev(self):
        return np.sqrt(self.variance)

    @property
    def pop_variance(self):
        return self.m2 / self.n

    @property
    def pop_std_dev(self):
        return np.sqrt(self.pop_variance)

    @property
    def sample_mode(self):
        mode = self.get_top_n_modes(1)
        if mode is not None:
            return mode[0][0]
        else:
            return None

    @property
    def mode(self):
        return self.sample_mode

    @property
    def mode_count(self):
        mode = self.get_top_n_modes(1)
        if mode is not None:
            return mode[0][1]
        else:
            return None

    @property
    def mins(self):
        return self._mins

    @property
    def maxes(self):
        return self._maxes


class Indexer(defaultdict):
    """ A data structure for assigning unique indexes (ids) to a collection of items.
        Provided items must be hashable
    """

    def __init__(self, items=None):
        super(Indexer, self).__init__(lambda: len(self))
        items = items or []
        self.extend(items)

    def extend(self, items):
        for item in items:
            self.add(item)

    def add(self, item):
        return self[item]

    def flip(self):
        return dict((idx,key) for key, idx in self.items())

    def ordered_keys(self):
        return [k for k,v in self.items()]

    def items(self):
        items = super(Indexer, self).items()
        return sorted(items, key=operator.itemgetter(1))

    def __repr__(self):
        return 'Indexer({0})'.format(repr(self.ordered_keys()))


class keydefaultdict(defaultdict):
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError( key )
        else:
            ret = self[key] = self.default_factory(key)
            return ret


class filemap(keydefaultdict):
    def __init__(self, default_factory, root=None, 
                                        extension=None, 
                                        mode='r',
                                        opener=open):
        self.name_factory = default_factory
        self.extension = extension
        self.mode = mode
        self.opener = open
        super(filemap, self).__init__(self.get_file_for)
        self.root = root

    def __enter__(self):
        return self
    
    def __exit(self):
        self.close()
    
    def get_path_for(self, obj):
        name = self.name_factory(obj)
        if self.extension:
            name = "{0}.{1}".format(name, self.extension)
        path = os.path.join(self.root, name)
        return path

    def get_file_for(self, obj):
        path = self.get_path_for(obj)
        io = self.opener(path, self.mode)
        return io

    def close(self):
        for key in self:
            try:
                self[key].close()
            except:
                pass
        
