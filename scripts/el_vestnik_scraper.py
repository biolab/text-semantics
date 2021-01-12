import json
import os
import pickle
import re
import unicodedata
import warnings
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tika import parser
from urllib3.exceptions import InsecureRequestWarning


warnings.filterwarnings("ignore", category=InsecureRequestWarning)


base_url = "https://ev.fe.uni-lj.si/"
list_url = "https://ev.fe.uni-lj.si/online-slo.php?vol={}"
list_range = range(87, 72, -1)


def get_articles():
    articles = []
    for vol in list_range:
        response = requests.get(list_url.format(vol), verify=False)
        html = response.content
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("div", id="vsebina").table
        articles += [
            (x.text, x["href"])
            for x in table.find_all("a")
            if x["href"].endswith(".pdf")
        ]
    return articles


if os.path.isfile("articles_elv.pkl"):
    with open("articles_elv.pkl", "rb") as f:
        all_articles = pickle.load(f)
else:
    all_articles = get_articles()
    with open("articles_elv.pkl", "wb") as f:
        pickle.dump(all_articles, f)


def donwload_pdf(url):
    r = requests.get(url, stream=True, verify=False)
    file = os.path.basename(urlparse(url).path)
    path = f"/tmp/{file}"
    with open(path, "wb") as fd:
        for chunk in r.iter_content(2000):
            fd.write(chunk)
    return path


def clean(path):
    os.remove(path)


def get_text(path):
    raw = parser.from_file(path)
    content = unicodedata.normalize("NFC", raw["content"])
    content = "\n".join(item.strip() for item in content.splitlines())
    content = content.replace(
        "Priprava prispevka za Elektrotehniški vestnik", ""
    )
    content = content.replace("IZVIRNI ZNANSTVENI ČLANEK ", "")
    content = re.sub("ELEKTROTEHNIŠKI VESTNIK.*?\\n", "", content)
    content = re.sub("\\nLITERATURA.*$", "", content, flags=re.DOTALL)
    return content.strip()


def remove_empty_lines(txt):
    """
    replace("\n\n", "\n") does not work in cases with more than two empty
    consective empty lines
    """
    return "\n".join(t for t in txt.splitlines() if t.strip())


def extract_abstract(text):
    # if not ključne besede - english paper
    if "Ključne besede" not in text:
        return None
    res = re.search(
        "Povzetek(\.|:| [–-])(.*?)Ključne besede:", text, flags=re.DOTALL
    )
    return remove_empty_lines(res.group(2)).strip()


def extract_keywords(text):
    res = re.search("Ključne besede:(.*?)\\n\\n", text, flags=re.DOTALL)
    return [x.strip() for x in res.group(1).split(",")]


def extract_text(text):
    res = re.search("(1 UVOD|1. UVOD).*$", text, re.DOTALL | re.IGNORECASE)
    if not res:
        # it will happen when no chapter UVOD - articles difficult to scrape
        # skip
        print("Skip: missing UVOD")
        return None
    text = res.group()
    return remove_empty_lines(text).strip()


def scrape_single_article(article):
    title, url = article
    full_url = urljoin(base_url, url)
    print("Scrapping:", full_url)
    path = donwload_pdf(full_url)
    text = get_text(path)
    if "introduction" in text.lower() and (
        "conclusion" in text.lower() or "references" in text.lower()
    ):
        return None

    clean(path)
    abstract = extract_abstract(text)
    if abstract is None:
        return None
    keywords = extract_keywords(text)
    body_text = extract_text(text)
    if not body_text:
        return None

    print(len(keywords), len(abstract), len(text))
    if len(keywords) < 3 or len(abstract) < 400 or len(text) < 10000:
        print("!!!!!!!!!!!!!!!")

    return {
        "Title": title,
        "Abstract": abstract,
        "Keywords": keywords,
        "Text": body_text,
        "URL": full_url,
    }


def scrape_articles(articles):
    all_articles = []
    for i, art in enumerate(articles[:]):
        print(f"--- {i} ---------------------")
        res = scrape_single_article(art)
        if res:
            all_articles.append(res)

    return all_articles


def prepare_for_server(df):
    dir_name = "elektrotehniski-vestnik-clanki"
    os.makedirs(dir_name)

    # save articles to txt files
    filenames = []
    for _, row in df.iterrows():
        filename = re.sub('[-]+', '-', (
            row["Title"]
            .lower()
            .replace(" ", "-")
            .replace(":", "")
            .replace("/", "")
            .replace(",", "")
            .replace(".", "")
            .replace("\t", "")
            [:60]
            + ".txt"
        ))
        with open(os.path.join(dir_name, filename), "w") as f:
            f.write(row["Text"])
        filenames.append(filename)
    df["Text file"] = filenames
    df = df.drop("Text", axis=1)
    df.to_csv(os.path.join(dir_name, "metadata.csv"), index=False)


if not os.path.isfile("el_vestnik_articles.csv"):
    artciles = scrape_articles(all_articles)
    with open("el_vestnik_articles.json", "w", encoding="utf-8") as f:
        json.dump(artciles, f, ensure_ascii=False, indent=4)

    df = pd.DataFrame(artciles)
    df.to_csv("el_vestnik_articles.csv", index=False)

    print(len(df))
    # it should be zero - no missing text
    print(((df["Text"].values == "") | (df["Text"].isna())).sum())
else:
    df = pd.read_csv("el_vestnik_articles.csv")

prepare_for_server(df)
