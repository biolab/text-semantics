import os
import tarfile
import time
import urllib.request
from collections import Counter

import bson
import pandas as pd
from bs4 import BeautifulSoup

# url to source
FILE_URL = (
    "https://podatki.gov.si/dataset/a989ca8a-08be-4b87-a0ad-a7b6991f387d/"
    "resource/b37e18dd-d80e-4327-872e-5f1b355ccc3b/download/vsebina.tar.gz"
)

# download dir
FILE_DIR = "files/"
FILE_NAME = os.path.join(FILE_DIR, os.path.basename(FILE_URL))
UNPACKED_FILE_NAME = os.path.join(FILE_DIR, "vsebina.bson", "pisrs", "vsebina.bson")

# file to pickle to
PICKLE_NAME = os.path.join(FILE_DIR, os.path.basename(FILE_URL) + ".df.pkl")

# result file
RESULTING_FILE_NAME = os.path.join(FILE_DIR, "zakoni-full.csv")

# types to scrape
# TYPES = {'PRAV', 'ZAKO', 'URED', 'SKLE'}
TYPES = {"ZAKO"}


def download_laws():
    """ Download a tar.gz with file """
    print("downlaoding")
    if not os.path.isfile(FILE_NAME):
        urllib.request.urlretrieve(FILE_URL, FILE_NAME)


def unpack_laws():
    """ Laws are packed in tar.gz, unpack them """
    print("extracting")
    if not os.path.isfile(UNPACKED_FILE_NAME):
        tar = tarfile.open(FILE_NAME, "r:gz")
        tar.extractall(FILE_DIR)
        tar.close()


def extract_laws():
    """ Extract data from bson file and pickle them """
    print("loading bson")
    with open(UNPACKED_FILE_NAME, "rb") as f:
        data = bson.decode_all(f.read())
    df = pd.DataFrame(data)
    df = df[df["idPredpisa"].str.contains("|".join(TYPES))]
    df = df.drop(["_id", "cleni", "cleniList"], axis=1)
    return df


def remove_duplicates(df):
    def replace_with_newer_regulations(s):
        # find all regulations that change s
        df_chng = df[df["idPredpisaChng"] == s["idPredpisa"]]
        # if not existing - return s
        if len(df_chng) == 0:
            return s
        # else replace regulations with newer version -
        # newer is one that changes s and have highest npb number
        new_s = df_chng.iloc[df_chng["npbNum"].argmax()]
        while new_s["vsebina"] is None:
            print(new_s["idPredpisa"], new_s["npbNum"])
            df_chng = df_chng[df_chng["npbNum"] != new_s["npbNum"]]
            new_s = df_chng.iloc[df_chng["npbNum"].argmax()]
        new_s["idPredpisa"] = s["idPredpisa"]
        return new_s

    # find regulations that are a basis for later changes - those which do not
    # change any regulation are basis
    df_orig = df[df["idPredpisaChng"].isnull()]
    return df_orig.apply(replace_with_newer_regulations, axis=1)


# title is contained in html elements with following classes
# can be combination of more of them
title_classes = ["Vrstapredpisa", "Naslovpredpisa", "NPB"]


def last_title_tag(div):
    """ Find the last html element that is a part of the law title """
    start = None
    for c in title_classes:
        start = div.find("p", {"class": c})
        if start is not None:
            break

    while True:
        next = start.find_next_sibling()
        if next.has_attr("class") and len(set(next["class"]) & set(title_classes)) > 0:
            start = next
        else:
            return start


def extract_text(div):
    """ Extract law text """
    start = last_title_tag(div)
    text = []
    for s in start.find_next_siblings():
        text.append(s.get_text())
    return "\n".join(text).replace("\n\n", "\n")


def extract_title(div):
    """ Extract law title """
    title = []
    # title can be in one of the following fields
    for c in title_classes:
        # find all since sometimes more instances of same class
        title_part = div.find_all("p", {"class": c})
        for p in title_part:
            title.append(p.get_text())
    return " ".join(title)


def print_metadata(row):
    """ Print metadata in readable format """
    text = "-" * 20 + "\n"
    text += f"idPredpisa: {row['idPredpisa']}\n"
    text += f"idPredpisaChang: {row['idPredpisaChng']}\n"
    text += f"npbNum: {row['npbNum']}\n"
    text += f"path: {row['path']}\n"
    text += f"sopPredpisa: {row['sopPredpisa']}\n"
    text += f"sopPredpisaChng: {row['sopPredpisaChng']}"
    print(text)


skip = [
    ("ZAKO525", 0),  # law is an image
    # not really laws - wrong labels
    ("ZAKO4611", 0),
    ("ZAKO5516", 0),
    ("ZAKO4295", 0),
    ("ZAKO7575", 0),
    ("ZAKO8188", 0),
    ("ZAKO7769", 0),
]


def extract_content_columns(df):
    print("parsing laws")
    res = []
    idxs = []
    for i, (idx, row) in enumerate(df.iterrows()):
        # print_metadata(row)
        print(i, "/", len(df), ":", row["idPredpisa"], row["npbNum"])
        if (row["idPredpisa"], row["npbNum"]) in skip or row["vsebina"] is None:
            print("skipped")
            continue

        # printing documents to html for visualisation
        with open(
            f"files/htmls/{row['idPredpisa']}_{row['npbNum']}_{i}.html", "w"
        ) as f:
            f.write(row["vsebina"])

        soup = BeautifulSoup(row["vsebina"], "html.parser")
        body = soup.body
        divs = body.findAll("div", recursive=False)
        if len(divs) > 1:
            print("More divs")

        text = extract_text(divs[0])
        title = extract_title(divs[0])
        assert len(text) > 10
        assert len(title) > 10

        res.append({"naslov": title, "vsebina": text})
        idxs.append(idx)
    return pd.DataFrame(res, index=idxs)


def extract_data(df):
    """ extract content and merge with metadata """
    # {'PRAV': 6713, 'ZAKO': 4072, 'URED': 3982, 'SKLE': 3876}
    print(Counter(df["idPredpisa"].str[:4]))
    print(df.columns)

    content = extract_content_columns(df)
    df = df[df.columns.difference(content.columns)]
    df = pd.concat((df, content), axis=1, join="inner")
    return df


if __name__ == "__main__":
    t = time.time()
    if not os.path.isfile(PICKLE_NAME):
        download_laws()
        unpack_laws()
        df = extract_laws()
        df.to_pickle(PICKLE_NAME)

    df = pd.read_pickle(PICKLE_NAME)
    df = remove_duplicates(df)
    df = extract_data(df)
    print(len(df))

    df.to_csv(RESULTING_FILE_NAME, index=False)
    print(f"total time = {time.time() - t} s")
