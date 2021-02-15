"""
Module was removed from gensim - this is a fixed copy.

This module contains implementation of SyntacticUnit class. It is generally 
used while text cleaning.
:class:`~gensim.summarization.syntactic_unit.SyntacticUnit` represents printable 
version of provided text.

"""


class SyntacticUnit(object):
    """SyntacticUnit class.

    Attributes
    ----------
    text : str
        Input text.
    token : str
        Tokenized text.
    tag : str
        Tag of unit, optional.
    index : int
        Index of syntactic unit in corpus, optional.
    score : float
        Score of synctatic unit, optional.

    """

    def __init__(self, text, token=None, tag=None, index=-1):
        """

        Parameters
        ----------
        text : str
            Input text.
        token : str
            Tokenized text, optional.
        tag : str
            Tag of unit, optional.

        """
        self.text = text
        self.token = token
        self.tag = tag[:2] if tag else None  # Just first two letters of tag
        self.index = index
        self.score = -1

    def __str__(self):
        return "Original unit: '" + self.text + "' *-*-*-* " + "Processed unit: '" + self.token + "'"

    def __repr__(self):
        return str(self)
