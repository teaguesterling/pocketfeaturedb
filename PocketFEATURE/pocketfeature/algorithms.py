#!/usr/bin/env python

from __future__ import division

from collections import defaultdict
from operator import itemgetter

import numpy as np
from munkres import Munkres


def cutoff_tanimoto_similarity(cutoffs, a, b, zeroed=False):
    """ Compute the PocketFEATURE tanimoto similarity of two FEATURE vectors
        This method takes two vectors and treats each pair of elments matched
        they differ by less than the supplied cutoff for that index.
        The number matched elements is then divided by the total number of
        elements "present" (e.g. non-zero) and this value returned as 
        the score.
        If zeroed is false, the elements also need the same sign.
    """
    union = np.logical_or(a != 0, b != 0)
    if not zeroed:
        same_sign = np.sign(a) == np.sign(b)
        union = np.logical_and(same_sign, union)
    union_size = np.count_nonzero(union)
    if union_size > 0:
        delta = np.abs(a[union] - b[union])
        intersection = delta < cutoffs[union]
        intersection_size = np.count_nonzero(intersection)
        return intersection_size / union_size
    else:
        return 0


def normalize_score(score, mode):
    return 2 / (1 + (score / mode) ** 2) - 1


def unique_product(p, q, skip=0):
    for i, x in enumerate(p, start=skip):
        for y in q[i:]:
            yield x,y


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
    chosen_keys = set()
    ordered_items = sorted(scores.items(), key=itemgetter(1), reverse=maximize)
    for keys, value in ordered_items:
        if not any(key in chosen_keys for key in keys):
            chosen_keys.update(keys)
            accepted.append((keys, value))
    return accepted


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

    def __init__(self, n=0, mean=None, m2=None, mins=None, maxes=None):
         self.reset(n=n, mean=mean, m2=m2, mins=mins, maxes=maxes)

    def reset(self, n=0, mean=None, m2=None, mins=None, maxes=None):
        if mean is None:
            mean = np.zeros(1)
        if m2 is None:
            m2 = np.zeros(1)
        if mins is None:
            mins = np.zeros(1)
        if maxes is None:
            maxes = np.zeros(1)

        self._n = n
        self._mean = np.array(mean)
        self._m2 = np.array(m2)
        self._mins = np.array(mins)
        self._maxes = np.array(maxes)

    def record(self, item):
        sample = np.array(item)

        n = self.n + 1
        delta = sample - self._mean
        mean = self._mean + delta / n
        m2 = self._m2 + delta * (sample - mean)
        mins = np.minimum(self._mins, sample)
        maxes = np.maximum(self._maxes, sample)

        self._n = n
        self._mean = mean
        self._m2 = m2
        self._mins = mins
        self._maxes = maxes

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

        cls = type(self)
        return cls(n=n, mean=mean, m2=m2, mins=mins, maxes=maxes)

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
    def mins(self):
        return self._mins

    @property
    def maxes(self):
        return self._maxes


class Indexer(defaultdict):
    """ A data structure for assigning unique indexes (ids) to a collection of items.
        Provided items must be hashable
    """

    def __init__(self, items=[]):
        super(Indexer, self).__init__(lambda: len(self))
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
        return sorted(items, key=itemgetter(1))

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
        
