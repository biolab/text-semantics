from flair.data import Sentence
from flair.embeddings import WordEmbeddings
from textsemantics.specific_words import cos_sim
import numpy as np


def precision(x_pred, x_true):
    return (len([x for x in x_pred if x in x_true]) / len(x_pred)) if len(x_pred) else 0


def recall(x_pred, x_true):
    return (len([x for x in x_pred if x in x_true]) / len(x_true)) if len(x_true) else 0


def embed_list(word_list):
    emb_list = list()
    embedder = WordEmbeddings('sl')
    for words in word_list:
        sent = Sentence(' '.join(words))
        embedder.embed(sent)
        emb_list.append([t.embedding.cpu().detach().numpy() for t in sent.tokens])
    return emb_list


def max_similarity(x_pred, x_true):
    ms = list()
    for x in x_true:
        ms.append(max([cos_sim(x, y) for y in x_pred]))

    return sum(ms) / len(ms)


def average_precision(x_pred, x_true):
    return (sum(precision(p, t) for p, t in zip(x_pred, x_true)) / len(x_pred)) if len(x_pred) else 0


def average_recall(x_pred, x_true):
    return (sum(recall(p, t) for p, t in zip(x_pred, x_true)) / len(x_pred)) if len(x_pred) else 0


def average_f_score(x_pred, x_true):
    f_scores = []
    for p, t in zip(x_pred, x_true):
        pr, re = precision(p, t), recall(p, t)
        f_scores.append(2 * pr * re / (pr + re) if (pr + re) else 0)
    return (sum(f_scores) / len(x_pred)) if len(x_pred) else 0


def average_max_similarity(x_pred, x_true):
    return (sum(max_similarity(p, t) for p, t in zip(x_pred, x_true)) / len(x_pred)) if len(x_pred) else 0


def take_n(l, n):
    return [x[:n] for x in l]


def score_in_len_range(predictions, keywords, score_method, embeddings=False):
    scores = []
    if embeddings:
        predictions = embed_list(take_n(predictions, 20))
        keywords = embed_list(keywords)

    for i in range(1, 21):
        scores.append(score_method(take_n(predictions, i), keywords))
    return scores
