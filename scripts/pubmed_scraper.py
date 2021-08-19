"""
Script downloads articles' metadata and abstracts from the PubMed library.
It was originally designed to download all articles with the mesh term longevity

Script saves metadata and abstract in the format for text-semantics repozitory.
"""

import os
from typing import List, Optional, Dict
from xml.etree import ElementTree

import pandas as pd
import requests

term = "longevity[MeSH%20Terms]"
retmax = 100000  # max number of results
search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retmax={retmax}"
fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids}&retmode=xml"
restult_dir = "pubmed_longevity"


def get_ids() -> List[str]:
    """
    Retrieve articles ids for the selected term.
    https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch

    Returns
    -------
    List containing articles' ids
    """
    response = requests.get(search_url.format(term=term, retmax=retmax))
    root = ElementTree.fromstring(response.content)
    id_list = root.find("IdList")
    ids = [id_.text for id_ in id_list]
    return ids


def get_mesh_terms(medline_c: ElementTree) -> List[str]:
    """ Extracts and returns the list of mesh terms for an article """
    ml = medline_c.find("MeshHeadingList")
    return [m.find("DescriptorName").text for m in ml]


def get_keywords(medline_c: ElementTree) -> Optional[List[str]]:
    """ Extracts and returns the list of keywords if provided """
    kw = medline_c.find("KeywordList")
    if kw is None:
        return None
    return [k.text for k in kw]


def get_title(article: ElementTree) -> str:
    """ Extracts and returns article's title """
    title = "".join(article.find("ArticleTitle").itertext()).strip("[]")
    if title.endswith("]."):
        title = title[:-2]
    return title


def get_authors(article: ElementTree) -> Optional[List[str]]:
    """ Extracts list of authors in FirstName LastName format """
    authorlist = article.find("AuthorList")
    if authorlist is None:
        # there are rare articles that are missing authors
        return None
    # some Author tags do not have actual names but are used for the location
    return [
        " ".join(
            a.find(el).text
            for el in ("ForeName", "LastName")
            if a.find(el) is not None
        )
        for a in authorlist
        if a.find("LastName") is not None
    ]


def get_date(article: ElementTree) -> int:
    """
    Extracts the year of the article. If ArticleDate exist use its year
    otherwise use the year form JournalIssue
    """
    d = article.find("ArticleDate")
    if d is not None:
        return int(d.find("Year").text)
    d = article.find("Journal").find("JournalIssue").find("PubDate")
    y = d.find("Year")
    if y is not None:
        return int(y.text)
    return int(d.find("MedlineDate").text.split(" ")[0].split("-")[0])


def fetch_data(ids: List[str]) -> List[Dict]:
    """
    Fetch data for articles with provided ids and returns them as a list of
    dicts. Dict contain metadata and abstract.

    Parameters
    ----------
    ids: The list of article ids to fetch

    Returns
    -------
    List of metadata dicts for every article.
    """
    chunks = [ids[x : x + 50] for x in range(0, len(ids), 50)]
    results = []
    for i, c in enumerate(chunks):
        print(f"fetching chunk {i}/{len(chunks)}")
        response = requests.get(fetch_url.format(ids=",".join(c)))
        root = ElementTree.fromstring(response.content)
        assert len(root) == len(c)
        for pmarticle, id_ in zip(root, c):
            print(id_)
            medline_citation = pmarticle.find("MedlineCitation")
            article = medline_citation.find("Article")
            journal = article.find("Journal")
            abstract = article.find("Abstract")
            if abstract is None:
                print("skipped", id_)
                continue
            abstract = "\n".join(
                "".join(a.itertext()) for a in abstract.findall("AbstractText")
            )

            data = {
                "title": get_title(article),
                "abstract": abstract,
                "journal": journal.find("Title").text,
                "authors": get_authors(article),
                "mesh_terms": get_mesh_terms(medline_citation),
                "keywords": get_keywords(medline_citation),
                "pubmed_id": id_,
                "year": get_date(article),
            }
            results.append(data)

    return results


def save_data(df: pd.DataFrame) -> List[str]:
    """
    Save abstracts in files and return list of files names which needst to be
    included in the metadata.

    Parameters
    ----------
    df: Pandas dataframe with metadata and abstracts

    Returns
    -------
    List of abstract file names
    """
    if not os.path.isdir(restult_dir):
        os.mkdir(restult_dir)
    abstract_files = []
    for i, r in df.iterrows():
        filename = f"{r['pubmed_id']}.txt"
        with open(f"{restult_dir}/{filename}", "w") as f:
            f.write(r["abstract"])
        abstract_files.append(filename)
    return abstract_files


all_ids = get_ids()
data = fetch_data(all_ids)
print("num all results:", len(all_ids))
print("num all fetched articles:", len(data))

df = pd.DataFrame(data)
df.to_pickle("pubmed_longevity.pkl")
df["abstract_file"] = save_data(df)
df = df.drop("abstract", axis=1)
df.to_csv(fr"{restult_dir}/metadata.csv", index=False)
