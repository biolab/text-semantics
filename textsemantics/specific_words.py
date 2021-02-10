import string
from typing import List, Optional, Callable, Tuple, Dict, Set

import langcodes
import nltk
import numpy as np
import yake
from flair.data import Sentence
from flair.embeddings import WordEmbeddings
from lemmagen import (
    DICTIONARY_SLOVENE,
    DICTIONARY_ENGLISH,
    DICTIONARY_SERBIAN,
    DICTIONARY_ITALIAN,
    DICTIONARY_ROMANIAN,
    DICTIONARY_HUNGARIAN,
    DICTIONARY_FRENCH,
    DICTIONARY_GERMAN,
    DICTIONARY_SPANISH,
    DICTIONARY_CZECH,
    DICTIONARY_BULGARIAN,
    DICTIONARY_ESTONIAN,
)
from lemmagen.lemmatizer import Lemmatizer
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

from textsemantics.textrank import keywords as textrank_kw
from textsemantics.utils import cos_sim
from textsemantics.utils.udpipe import get_udipipe_lematizer
from textsemantics.utils.word_enrichment import hypergeom_p_values


lemmagen_languages = {
    "slovenian": DICTIONARY_SLOVENE,
    "english": DICTIONARY_ENGLISH,
    "serbian": DICTIONARY_SERBIAN,
    "italian": DICTIONARY_ITALIAN,
    "romanian": DICTIONARY_ROMANIAN,
    "hungarian": DICTIONARY_HUNGARIAN,
    "french": DICTIONARY_FRENCH,
    "german": DICTIONARY_GERMAN,
    "spanish": DICTIONARY_SPANISH,
    "czech": DICTIONARY_CZECH,
    "bulgarian": DICTIONARY_BULGARIAN,
    "estonian": DICTIONARY_ESTONIAN,
}


def _get_lemmatizer(language: str) -> Callable:
    if language in lemmagen_languages:
        return Lemmatizer(
            dictionary=lemmagen_languages[language.lower()]
        ).lemmatize
    else:
        return get_udipipe_lematizer(language)


def nltk_language(language: str) -> str:
    exceptions = {"slovenian": "slovene"}
    return exceptions.get(language, language)


def _preprocess_corpus(corpus: List[str], language: str) -> List[List[str]]:
    nltk.download("stopwords", quiet=True)
    lemmatizer = _get_lemmatizer(language)
    stop_words = set(stopwords.words(nltk_language(language.lower())))
    tokenizer = nltk.RegexpTokenizer("\w+")

    preprocessed = list()
    for text in corpus:
        text = text.translate(text.maketrans("", "", string.punctuation))
        tokens = tokenizer.tokenize(text.lower())
        tokens = [
            lemmatizer(token)
            for token in tokens
            if token not in stop_words
            and len(token) > 2
            and not token.isnumeric()
        ]
        # lematizer in rare cases produce empty strings - removing them
        tokens = list(filter(lambda a: a != "", tokens))
        preprocessed.append(tokens)
    return preprocessed


def prepare_embeddings(
    tokens_list: List[List[str]],
) -> Tuple[
    np.ndarray, Dict[str, np.ndarray], Dict[str, Set[int]], List[Set[str]]
]:
    embedder = WordEmbeddings("sl")
    word_embs = {}
    doc_embs = list()
    doc2word = list()
    word2doc = dict()

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
            if token.text not in word_embs:
                word_embs[token.text] = emb
        doc_embs.append(doc_emb)

    doc_embs = np.array(doc_embs)

    return doc_embs, word_embs, word2doc, doc2word


def find_corpus_words(
    doc_embs: np.ndarray, word_embs: Dict[str, np.ndarray]
) -> List[List[Tuple[str, float]]]:
    # compute distances
    distances = np.zeros((len(word_embs), doc_embs.shape[0]))
    words = list(word_embs.keys())
    for i, word in enumerate(words):
        for j in range(doc_embs.shape[0]):
            distances[i, j] = 1 - cos_sim(word_embs[word], doc_embs[j, :])

    # compute scores
    doc_desc = []
    for j in range(doc_embs.shape[0]):
        scores = np.zeros(len(word_embs))
        for i in range(len(words)):
            mask = np.full(doc_embs.shape[0], fill_value=True)
            mask[j] = False
            scores[i] = distances[i, j] - np.mean(distances[i, mask])

        idx = np.argsort(scores)
        doc_desc.append([(words[w], scores[w]) for w in idx])
    return doc_desc


def find_document_words(
    doc_embs: np.ndarray,
    word_embs: Dict[str, np.ndarray],
    word2doc: Dict[str, Set[int]],
    doc2word: List[Set[str]],
) -> List[List[Tuple[str, float]]]:
    distances = dict()
    for word, w_emb in word_embs.items():
        for j in word2doc[word]:
            distances[word, j] = 1 - cos_sim(w_emb, doc_embs[j, :])

    doc_desc = list()
    for j in range(doc_embs.shape[0]):
        scores = np.zeros(len(doc2word[j]))
        ind2word = dict(zip(list(range(len(doc2word[j]))), list(doc2word[j])))
        for k, word in enumerate(doc2word[j]):
            # current document and a single word
            sum_of_distances = sum([distances[word, x] for x in word2doc[word]])
            if len(word2doc[word]) > 1:
                mean_distance = (sum_of_distances - distances[word, j]) / (
                    len(word2doc[word]) - 1
                )
            else:
                mean_distance = 0
            scores[k] = distances[word, j] - mean_distance
        idx = np.argsort(scores)
        doc_desc.append([(ind2word[x], scores[x]) for x in idx])
    return doc_desc


def embedding_corpus_keywords(
    texts: Optional[List[str]] = None,
    tokens: Optional[List[List[str]]] = None,
    language: str = "slovenian",
):
    assert bool(texts) != bool(
        tokens
    ), "Parametri naj vsebujejo zgolj besedilo ali zgolj pojavnice"
    if not tokens:
        tokens = _preprocess_corpus(texts, language)
    doc_embs, word_embs, _, _ = prepare_embeddings(tokens)
    return find_corpus_words(doc_embs, word_embs)


def embedding_document_keywords(
    texts: Optional[List[str]] = None,
    tokens: Optional[List[List[str]]] = None,
    language: str = "slovenian",
):
    assert bool(texts) != bool(
        tokens
    ), "Parametri naj vsebujejo zgolj besedilo ali zgolj pojavnice"
    if not tokens:
        tokens = _preprocess_corpus(texts, language)
    doc_embs, word_embs, word2doc, doc2word = prepare_embeddings(tokens)
    return find_document_words(doc_embs, word_embs, word2doc, doc2word)


def enrichment_keywords(
    texts: Optional[List[str]] = None,
    tokens: Optional[List[List[str]]] = None,
    background_texts: Optional[List[str]] = None,
    background_tokens: Optional[List[List[str]]] = None,
    language: str = "slovenian",
):
    assert bool(texts) != bool(
        tokens
    ), "Parametri naj vsebujejo zgolj besedilo ali zgolj pojavnice"
    if not tokens:
        tokens = _preprocess_corpus(texts, language)

    assert (
        bool(background_texts) != bool(background_tokens),
        "Parametri naj vsebujejo zgolj besedilo (background text) ali zgolj "
        "pojavnice (background tokens)",
    )
    if not background_tokens:
        background_tokens = _preprocess_corpus(texts, language)

    temp_tokes = tokens + background_tokens
    joined_texts = [" ".join(tokens) for tokens in temp_tokes]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(joined_texts)
    words = vectorizer.get_feature_names()

    keywords = []
    for row in X[: len(tokens)]:
        p_values = hypergeom_p_values(X[len(tokens) :], row)
        order = np.argsort(p_values)
        keywords.append([(words[i], p_values[i]) for i in order])

    return keywords


def tfidf_keywords(
    texts: Optional[List[str]] = None,
    tokens: Optional[List[List[str]]] = None,
    language: str = "slovenian",
):
    assert bool(texts) != bool(
        tokens
    ), "Parametri naj vsebujejo zgolj besedilo ali zgolj pojavnice"
    if not tokens:
        tokens = _preprocess_corpus(texts, language)

    joined_texts = [" ".join(tokens) for tokens in tokens]
    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(joined_texts)
    words = vectorizer.get_feature_names()

    keywords = []
    for row in X:
        features = [(words[i], row[0, i]) for i in row.nonzero()[1]]
        keywords.append(sorted(features, key=lambda tup: tup[1], reverse=True))
    return keywords


def yake_keywords(
    texts: List[str], language: str = "slovenian", max_len: int = 1
):
    # yake uses lancodes instead of full language name
    lg = langcodes.find(language).language
    yake_extractor = yake.KeywordExtractor(lan=lg, n=max_len)
    return [yake_extractor.extract_keywords(txt) for txt in texts]


def text_rank_keywords(
    texts: Optional[List[str]] = None,
    tokens: Optional[List[List[str]]] = None,
    language: str = "slovenian",
    num_words: int = 20,
    keyphrases: bool = False,
):
    assert bool(texts) != bool(
        tokens
    ), "Parametri naj vsebujejo zgolj besedilo ali zgolj pojavnice"
    if not tokens:
        tokens = _preprocess_corpus(texts, language)

    def text_rank(tokens):
        kw = textrank_kw(
            " ".join(tokens), words=num_words, scores=True, deacc=False
        )
        if not keyphrases:
            kw = [(x, sc) for w, sc in kw for x in w.split()]
        return kw

    return [text_rank(tokens) for tokens in tokens]
