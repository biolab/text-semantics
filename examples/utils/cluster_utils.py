import numpy as np
from textsemantics.utils import cos_sim


def find_cluster_words(doc_embs, word_embs, cluster_labels):
    # find unique cluster labels
    unique_clusters = [c for c in np.unique(cluster_labels) if c > -1]
    n_clusters = len(unique_clusters)

    # find centroids
    cluster_centroids = np.zeros((n_clusters, doc_embs.shape[1]))
    for c, c_label in enumerate(unique_clusters):
        cluster_centroids[c, :] = np.mean(
            doc_embs[cluster_labels == c_label], axis=0
        )

    # compute distances between centroids and words
    words = list(word_embs.keys())
    word_distance_vectors = np.zeros((len(words), n_clusters))
    for i, word in enumerate(words):
        for j, c_label in enumerate(unique_clusters):
            word_distance_vectors[i, j] = 1 - cos_sim(
                word_embs[word], cluster_centroids[j, :]
            )

    # describe clusters
    cluster_describer = dict()
    for c, c_label in enumerate(unique_clusters):
        cluster_describer[c_label] = list()
        cluster_metric = np.zeros(len(words))
        for i in range(len(words)):
            mask = np.full(n_clusters, fill_value=True)
            mask[c] = False
            cluster_metric[i] = word_distance_vectors[i, c] - np.mean(
                word_distance_vectors[i, mask]
            )
        inds = np.argsort(cluster_metric)
        for ind in inds:
            cluster_describer[c_label].append(words[ind])

    return cluster_describer
