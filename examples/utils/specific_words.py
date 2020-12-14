import numpy as np
from flair.data import Sentence
from flair.embeddings import WordEmbeddings


def prepare_data(tokens_list):
    embedder = WordEmbeddings('sl')
    words = list()
    word_embs = list()
    doc_embs = list()
    word2doc = dict()
    doc2word = list()

    for i, tokens in enumerate(tokens_list):
        sent = Sentence(" ".join(tokens))
        embedder.embed(sent)
        doc_emb = np.zeros(embedder.embedding_length)
        doc2word.append(set())
        for token in sent.tokens:
            if token.text not in word2doc:
                word2doc[token.text] = set()
            word2doc[token.text].add(i)
            doc2word[i].add(token.text)

            emb = token.embedding.cpu().detach().numpy()
            doc_emb += emb / len(tokens)
            if token.text not in words:
                words.append(token.text)
                word_embs.append(emb)
        doc_embs.append(doc_emb)

    doc_embs = np.array(doc_embs)
    word_embs = np.array(word_embs)

    return doc_embs, words, word_embs, word2doc, doc2word


def cos_sim(x, y):
    return x.dot(y) / np.linalg.norm(x) / np.linalg.norm(y)


def find_corpus_words(doc_embs, words, word_embs):

    # compute distances
    distances = np.zeros((word_embs.shape[0], doc_embs.shape[0]))
    for i in range(word_embs.shape[0]):
        for j in range(doc_embs.shape[0]):
            distances[i, j] = 1 - cos_sim(word_embs[i, :], doc_embs[j, :])

    # compute scores
    doc_desc = dict()
    for j in range(doc_embs.shape[0]):
        scores = np.zeros(word_embs.shape[0])
        for i in range(word_embs.shape[0]):
            mask = np.full(doc_embs.shape[0], fill_value=True)
            mask[j] = False
            scores[i] = distances[i, j] - np.mean(distances[i, mask])

        idx = np.argsort(scores)
        doc_desc[j] = [words[w] for w in idx]

    return doc_desc


def find_document_words(doc_embs, words, word_embs, word2doc, doc2word):

    word2ind = dict(zip(words, range(len(words))))
    distances = dict()
    for i in range(word_embs.shape[0]):
        word = words[i]
        for j in word2doc[word]:
            distances[i, j] = 1 - cos_sim(word_embs[i, :], doc_embs[j, :])

    doc_desc = list()
    for j in range(doc_embs.shape[0]):
        scores = np.zeros(len(doc2word[j]))
        ind2word = dict(zip(list(range(len(doc2word[j]))), list(doc2word[j])))
        for k, word in enumerate(doc2word[j]):
            # current document and a single word
            i = word2ind[word]
            sum_of_distances = sum([distances[i, x] for x in word2doc[word]])
            mean_distance = (sum_of_distances - distances[i, j]) / (doc_embs.shape[0] - 1)
            scores[k] = distances[i, j] - mean_distance
        idx = np.argsort(scores)
        doc_desc.append([ind2word[x] for x in idx])

    return doc_desc
