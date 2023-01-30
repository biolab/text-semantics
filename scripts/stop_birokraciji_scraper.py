import logging
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from unicodedata import normalize
from urllib.parse import urljoin

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup

BASE_URL = "https://www.stopbirokraciji.gov.si/"
CATEGORIES = (
    "dispatched",
    "replied",
    "concluded",
)
PROPOSAL_DONT_EXIST = "Pobuda uporabnika ne obstaja."

CSV_FILE = "stop-birokraciji.csv"
DESTINATION_DIRECTORY = "stop-birokraciji"


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def cleanup():
    """Remove directories and folders from previous scrapping"""
    logger.info("Removing files and directories form previous scraping")
    try:
        os.remove(CSV_FILE)
    except FileNotFoundError:
        logger.debug(f"{CSV_FILE} not found, removing skipped")
    try:
        shutil.rmtree(DESTINATION_DIRECTORY)
    except FileNotFoundError:
        logger.debug(f"{DESTINATION_DIRECTORY} not found, removing skipped")


def init():
    """Prepare folders for saving proposals"""
    logger.info(f"Creating {DESTINATION_DIRECTORY}")
    os.mkdir(DESTINATION_DIRECTORY)


def get_max_id_page(category: str) -> int:
    """Find maximal ID in category."""
    logger.info(f"Getting maximal proposal ID in category {category}")
    html = requests.get(urljoin(BASE_URL, f"pobude/?status_id={category}"))
    soup = BeautifulSoup(html.text, "html.parser")
    cards = soup.findAll("div", {"class": "card"})
    max_id = max(int(c.div.a["href"].split("pobuda/?st=")[1]) for c in cards)
    logger.info(f"Max ID for {category}: {max_id}")
    return max_id


def get_max_id() -> int:
    """
    Proposals can be retrieved through IDs. Since IDs are range numbers (first
    proposal has id=1), we first find out the number of the last proposal and
    the scrape all ids from 1 to max id.
    """
    logger.info("Getting maximal proposal ID")
    max_id = max(get_max_id_page(category) for category in CATEGORIES)
    logger.info(f"Maximal ID: {max_id}")
    return max_id


def get_comment_data(soup: BeautifulSoup, class_: str) -> Optional[str]:
    comment = soup.find("div", {"class", class_})
    return (
        comment.find("span", {"class", "comment-data-value"}).text.strip()
        if comment
        else None
    )


def get_timeline(soup: BeautifulSoup, class_: str) -> Optional[datetime]:
    tml = soup.find("li", {"class": class_})
    return datetime.strptime(tml.span.span.text, "%d. %m. %Y") if tml else None


def get_ezu(soup: BeautifulSoup) -> Tuple[Optional[datetime], Optional[str]]:
    ezu = soup.find("li", {"class": "ezu"})
    if ezu:
        return datetime.strptime(ezu.a.span.text, "%d. %m. %Y"), ezu.a["href"]
    return None, None


def get_response(soup: BeautifulSoup) -> Optional[str]:
    resp = soup.find("div", {"class": "comment-reply"})
    return resp.text if resp else None


def get_proposal(soup: BeautifulSoup) -> str:
    return "\n".join(t.text for t in soup.find("div", {"class": "comment-content"}))


def proposal_exists(soup: BeautifulSoup) -> bool:
    content = soup.find("div", {"class": "comment-content"})
    return content.h3 is None or content.h3.text.strip() != PROPOSAL_DONT_EXIST


def srap_single_page(page_id: int) -> Optional[Dict[str, Any]]:
    """Scrape proposal with ID == page_id"""
    url = urljoin(BASE_URL, f"pobuda/?st={page_id}")
    logger.info(f"Scrapping proposal from {url}")

    html = requests.get(url)
    soup = BeautifulSoup(html.text, "html.parser")
    if not proposal_exists(soup):
        logger.info(f"Proposal with ID {page_id} does not exist. Skipping.")
        return None

    ezu_date, ezu_url = get_ezu(soup)

    return {
        "ID pobude": page_id,
        "Naslov": soup.find("h1").text if soup.find("h1") else None,
        "URL": url,
        "Področje": get_comment_data(soup, "priority_area"),
        "Pristojni organ": get_comment_data(soup, "ministry"),
        "Pobuda oddana": get_timeline(soup, "submitted"),
        "Pobuda objavljena": get_timeline(soup, "published"),
        "Pobuda posredovana v odziv": get_timeline(soup, "dispatched"),
        "Pobuda sprejeta in zaključena": get_timeline(soup, "concluded"),
        "Pobuda uvrščena v EZU": ezu_date,
        "EZU URL": ezu_url,
        "Pobuda": get_proposal(soup),
        "Odgovor pristojnega organa": get_response(soup),
    }


def save_document(document: Dict[str, Any]):
    logger.info(f"Saving proposal with ID {document['ID pobude']}")
    file_name = normalize("NFKD", str(document["ID pobude"]))
    file_name = file_name.encode("ascii", "ignore").decode("utf-8")

    text_file = f"{file_name}.txt"
    with open(os.path.join(DESTINATION_DIRECTORY, text_file), "w") as f:
        f.write(document["Pobuda"])

    # add name file name and remove the text from dictionary, sav as yaml
    document = document.copy()
    document["Text file"] = text_file
    document.pop("Pobuda")

    with open(os.path.join(DESTINATION_DIRECTORY, f"{file_name}.yaml"), "w") as f:
        yaml.dump(document, f, default_flow_style=False)


def scrape_pages(max_id: int) -> pd.DataFrame:
    """
    Scrape all proposals. Proposals have ID from 1 to max_id. Iterate through
    IDs and scrape proposal for every ID.
    """
    logger.info("Starting proposal scrape")
    data = []
    for id_ in range(1, max_id + 1):
        proposal = srap_single_page(id_)
        if proposal is not None:
            data.append(proposal)
            save_document(proposal)
    logger.info("All proposal scrapped")
    return pd.DataFrame(data)


def main():
    cleanup()
    init()
    max_id = get_max_id()
    df = scrape_pages(max_id)
    df.to_csv(CSV_FILE, index=False)


if __name__ == "__main__":
    main()
