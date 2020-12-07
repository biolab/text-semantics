import re

regex = "(?<=(1\. člen\s)).+?(?=2\. člen)"


def find_first_article(doc):
    """
    Find everything between "1. člen" and "2. člen". Usually, this section
    defines the content of the law.
    :param doc: A string with document content.
    :return: The content of the document.
    """
    res = re.search(regex, doc, flags=re.MULTILINE|re.DOTALL)
    return ' '.join(res.group(0).split()) if res else ""


def get_abstract(docs):
    return [find_first_article(doc) for doc in docs]
