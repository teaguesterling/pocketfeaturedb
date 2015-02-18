from __future__ import print_function, division
import sys

from pylab import *
import numpy as np

from sklearn.metrics import roc_auc_score

from pocketfeature.io import matrixvaluesfile
from pocketfeature.algorithms import GaussianStats

cutoffs = [0.1, 0.1, 0, -0.1, -0.15, -0.2, -0.25, -0.3]


def make_all_plots(pos_file, cont_file):
    with open(pos_file) as f:
        positives = matrixvaluesfile.load(f, cast=float)

    with open(cont_file) as f:
        controls = matrixvaluesfile.load(f, cast=float)

    # Transpose to do cutoff-wise instead of pair-wise
    all_pos_scores = np.array(positives.values()).transpose()[3:, :]
    all_cont_scores = np.array(controls.values()).transpose()[3:, :]

    for i, cutoff in enumerate(cutoffs):
        pos_scores = all_pos_scores[i,2:]
        cont_scores = all_cont_scores[i, 2:]

        make_plot(pos_scores, cont_scores, cutoff)
        auc = compute_auc(pos_scores, cont_scores)
        print("{0:01.2f}\t{1:01.3f}".format(cutoff, auc))


def compute_auc(pos_scores, cont_scores):
    pos_labels = np.zeros(pos_scores.shape)
    cont_labels = np.ones(cont_scores.shape)
    scores = np.concatenate((pos_scores, cont_scores))
    labels = np.concatenate((pos_labels, cont_labels))

    return roc_auc_score(labels, scores)


def make_plot(pos_scores, cont_scores, cutoff, steps=50):
    pos_stats = get_stats(pos_scores)
    cont_stats = get_stats(cont_scores)

    low = min(pos_stats.mins, cont_stats.mins)
    high = 0.
    points = np.linspace(low, high, steps)

    curve_points = []
    for threshold in points:
        tp = len([p for p in pos_scores if p <= threshold])
        fp = len([p for p in cont_scores if p <= threshold])
        tn = len([p for p in cont_scores if p > threshold])
        fn = len([p for p in pos_scores if p > threshold])

        tpr = tp / (tp + fn)
        scp = tn / (tn + fp)
        fpr = 1 - scp
        
        point = (fpr, tpr)
        curve_points.append(point)

    curve = np.array(curve_points).transpose()
    FPR, TPR = curve

    clf()
    plot(FPR, TPR)
    title('PocketFEATURE ROC at point-score cutoff {}'.format(cutoff))
    xlabel("False Positive Rate (1-Sens)")
    ylabel("True Positive Rate (Spec)")
    savefig("ROC-c{0}.png".format(cutoff))

def get_stats(vals):
    stats = GaussianStats()
    for val in vals:
        stats.record(val)
    return stats


if __name__ == '__main__':
    sys.exit(make_all_plots(*sys.argv[1:]))
