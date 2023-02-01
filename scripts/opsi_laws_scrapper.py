import logging
import os
import shutil
import sys
import tarfile
import time
import urllib.request
from collections import Counter
from typing import List
from unicodedata import normalize

import bson
import pandas as pd
import yaml
from bs4 import BeautifulSoup, Tag

# url to source
SOURCE_URL = (
    "https://podatki.gov.si/dataset/a989ca8a-08be-4b87-a0ad-a7b6991f387d/"
    "resource/b37e18dd-d80e-4327-872e-5f1b355ccc3b/download/vsebina.tar.gz"
)
ROOT_DIRECTORY = "data"
ARCHIVE_FILE = os.path.join(ROOT_DIRECTORY, os.path.basename(SOURCE_URL))
UNPACKED_DIR = "vsebina.bson"
UNPACKED_FILE_NAME = "pisrs/vsebina.bson"
CSV_FILE = "regulstions.csv"
DESTINATION_DIRECTORY = "regulations"

# init logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def cleanup():
    """Remove directories and folders from previous scrapping"""
    logger.info("Removing files and directories form previous scraping")
    dir_ = os.path.join(ROOT_DIRECTORY, UNPACKED_DIR)
    try:
        shutil.rmtree(dir_)
    except FileNotFoundError:
        logger.debug(f"{dir_} not found, removing skipped")
    dir_ = os.path.join(ROOT_DIRECTORY, DESTINATION_DIRECTORY)
    try:
        shutil.rmtree(dir_)
    except FileNotFoundError:
        logger.debug(f"{dir_} not found, removing skipped")
    try:
        os.remove(os.path.join(ROOT_DIRECTORY, CSV_FILE))
    except FileNotFoundError:
        logger.debug(f"{CSV_FILE} not found, removing skipped")


def init():
    """Prepare folders for saving proposals"""
    logger.info(f"Creating {ROOT_DIRECTORY}")
    if not os.path.isdir(ROOT_DIRECTORY):
        os.mkdir(ROOT_DIRECTORY)

    dest_dir = os.path.join(ROOT_DIRECTORY, DESTINATION_DIRECTORY)
    logger.info(f"Creating {dest_dir}")
    os.mkdir(dest_dir)


def download_laws():
    """ Download a tar.gz with file """
    logger.info(f"Downloading data from {SOURCE_URL}")
    tic = time.time()
    urllib.request.urlretrieve(SOURCE_URL, ARCHIVE_FILE)
    logger.info(f"Downloaded in {round(time.time() - tic, 2)} s")


def unpack_laws():
    """regulations are downloaded as tar.gz. This function unpack the archive file"""
    logger.info(f"Extracting regulations archive")
    tar = tarfile.open(ARCHIVE_FILE, "r:gz")
    tar.extractall(ROOT_DIRECTORY)
    tar.close()


def extract_laws(types_: List[str]) -> pd.DataFrame:
    """
    Extract data from bson, parse as dataframe and keep only specified types
    """
    logger.info(f"Extracting {','.join(types_)} form {UNPACKED_FILE_NAME}")
    with open(os.path.join(ROOT_DIRECTORY, UNPACKED_DIR, UNPACKED_FILE_NAME), "rb") as f:
        data = bson.decode_all(f.read())

    df = pd.DataFrame(data)
    logger.info(f"Types in data: {Counter(df['idPredpisa'].str[:4])}")
    df = df[df["idPredpisa"].str.contains("|".join(types_))]
    df = df.drop(["_id", "cleni", "cleniList"], axis=1)
    logger.info(f"Extracted {len(df)} documents")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Regulations can be replaced with newer version - when regulation updated - filter
    dataframe to have only newest versions of each regulation
    """
    logger.info(f"Removing duplicates for regulations that have changed")

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
            df_chng = df_chng[df_chng["npbNum"] != new_s["npbNum"]]
            new_s = df_chng.iloc[df_chng["npbNum"].argmax()]
        new_s["idPredpisa"] = s["idPredpisa"]
        return new_s

    # find regulations that are a basis for later changes - those which do not
    # change any regulation are basis
    df_orig = df[df["idPredpisaChng"].isnull()]
    return df_orig.apply(replace_with_newer_regulations, axis=1)


# title contained in elements with following classes, also combination of them
title_classes = ["Vrstapredpisa", "Naslovpredpisa", "NPB"]


def last_title_tag(div: Tag) -> Tag:
    """ Find the last html element that is a part of the regulation title """
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


def extract_text(div: Tag) -> str:
    """ Extract regulation text """
    start = last_title_tag(div)
    text = []
    for s in start.find_next_siblings():
        text.append(s.get_text())
    return "\n".join(text).replace("\n\n", "\n")


def extract_title(div: Tag) -> str:
    """ Extract regulation title """
    title = []
    for c in title_classes:  # title can be in one of the following fields
        # find all since sometimes more instances of same class
        title_part = div.find_all("p", {"class": c})
        for p in title_part:
            title.append(p.get_text())
    return " ".join(title).replace('\n', ' ').replace('\r', '')


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


def extract_content_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Extract content information from regulations"""
    logger.info("Extracting the content information from regulations")
    res, idxs = [], []
    for i, (idx, row) in enumerate(df.iterrows()):
        logger.info(
            f"Extracting regulation {i}/{len(df)}: {row['idPredpisa']}-{row['npbNum']}"
        )
        if (row["idPredpisa"], row["npbNum"]) in skip or row["vsebina"] is None:
            logger.info(f"Skipping {row['idPredpisa']}-{row['npbNum']}")
            continue

        soup = BeautifulSoup(row["vsebina"], "html.parser")
        body = soup.body
        divs = body.findAll("div", recursive=False)
        if len(divs) > 1:
            logger.warning(
                f"{row['idPredpisa']}-{row['npbNum']} has more main divs"
                ", considering only first one."
            )

        text = extract_text(divs[0])
        title = extract_title(divs[0])
        assert len(text) > 10
        assert len(title) > 10

        res.append({"naslov": title, "vsebina": text})
        idxs.append(idx)
    return pd.DataFrame(res, index=idxs)


def extract_data(df: pd.DataFrame) -> pd.DataFrame:
    """Extract content and merge with metadata"""
    logger.info("Extracting regulations content")
    logger.info(f"Types in data: {Counter(df['idPredpisa'].str[:4])}")

    content = extract_content_columns(df)
    df = df[df.columns.difference(content.columns)]
    return pd.concat((df, content), axis=1, join="inner")


def save_documents(df: pd.DataFrame):
    for _, document in df.iterrows():
        logger.info(f"Saving proposal with ID {document['idPredpisa']}")
        file_name = normalize("NFKD", str(document["naslov"]))
        file_name = file_name.encode("ascii", "ignore").decode("utf-8")
        file_name = file_name.replace(" ", "-").replace("/", "-")[:100]
        dest_dir = os.path.join(ROOT_DIRECTORY, DESTINATION_DIRECTORY)

        text_file = f"{file_name}.txt"
        with open(os.path.join(dest_dir, text_file), "w") as f:
            f.write(document["vsebina"])

        # add name file name and remove the text from dictionary, sav as yaml
        document = document.to_dict()
        document["Text file"] = text_file
        document.pop("vsebina")

        with open(os.path.join(dest_dir, f"{file_name}.yaml"), "w") as f:
            yaml.dump(document, f, default_flow_style=False)


def extract(types_: List[str]):
    cleanup()
    init()
    if not os.path.isfile(ARCHIVE_FILE):
        download_laws()
    unpack_laws()
    df = extract_laws(types_)
    df = remove_duplicates(df)
    df = extract_data(df)
    save_documents(df)
    df.to_csv(os.path.join(ROOT_DIRECTORY, CSV_FILE), index=False)


if __name__ == "__main__":
    """
    Script must be called with space seperated type arguments:
    python opsi_law_scrapper.py ZAKO AKT_ ...
    """
    types_ = sys.argv[1:]
    assert len(types_) > 0, "Pass at least one type argument"
    extract(types_)
