import re


cleni = "[0-9]+\.[a-z]{0,1} člen[a]{0,1}"
dolocba = "([IVX]+\. )?(poglavje)?:?\s?(splošn[eai]|uvodn[eia]|temeljn[aie]) " \
          "določb[eia]"
precisceno = "Na podlagi .* je Državni zbor Republike Slovenije .* potrdil" \
             " uradno prečiščeno besedilo .*"
izdajam = "Na podlagi .* izdajam"
razglasam = "Razglašam .*, ki ga je sprejel Državni zbor Republike " \
            "Slovenije na .*"
veljava = "Ta zakon začne veljati petnajsti dan po objavi v Uradnem " \
          "listu Republike Slovenije."
uredba = "Uredba [0-9]+/[0-9]+/[A-Z]+"
uradni_list = "Uradni list [A-Z]+, št. [0-9]+/[0-9]+"
direktive = "(Direktiv[aeo]? |Sklep[a]? |Uredb[aei]? )?(št. )?(Sveta )?" \
            "[0-9]+/[0-9]+/[A-Z]+"


def remove_structure(doc):
    regex = [cleni, dolocba, precisceno, izdajam, razglasam,
             veljava, uredba, uradni_list, direktive]
    for r in regex:
        doc = re.sub(r, '', doc, flags=re.IGNORECASE)
    return doc


def filter_document(docs):
    """
    Remove structural parts of Slovenian laws. Structural parts refer to
     templates that are the same in most documents and are a part of legal
     texts.
    :param docs: list or pd.Series
    :return: list of documents without structural parts
    """
    return [remove_structure(doc) for doc in docs]
