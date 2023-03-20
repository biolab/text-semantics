"""
This is a script for scraping proposals to government webpage predlagam.valdi.si
Script scrapes all the proposals. And write them in the separate directory.
For every proposal it saves a .yaml file with metadata and separate files
with proposal texts, proposal, response (optinal - if response present),
and comments (optional - if comments present).
"""
import logging
import os
import shutil
import time
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

# init logging
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# global settings
BASE_URL = "https://predlagam.vladi.si/"
CATEGORIES = (
    "z-odzivom-organa",
    "zavrnjeni",
    "neustrezni",
    "zavrnjeni",
    "neustrezni",
)
ROOT_DIRECTORY = "data"
CSV_FILE = "predlogi-vladi.csv"
DESTINATION_DIRECTORY = "predlogi-vladi"


def cleanup():
    """Remove directories and folders from previous scrapping"""
    logger.info("Removing files and directories form previous scraping")
    try:
        shutil.rmtree(ROOT_DIRECTORY)
    except FileNotFoundError:
        logger.debug(f"{ROOT_DIRECTORY} not found, removing skipped")


def init():
    """Prepare folders for saving proposals"""
    logger.info(f"Creating {ROOT_DIRECTORY}")
    os.mkdir(ROOT_DIRECTORY)

    dest_dir = os.path.join(ROOT_DIRECTORY, DESTINATION_DIRECTORY)
    logger.info(f"Creating {dest_dir}")
    os.mkdir(dest_dir)


def init_browser() -> WebDriver:
    """Init browser required for scraping"""
    logger.info("Chrome browser init")
    op = webdriver.ChromeOptions()
    op.add_argument("headless")
    driver_service = ChromeService(ChromeDriverManager().install())
    browser = webdriver.Chrome(options=op, service=driver_service)
    logger.info("Chrome browser init done")
    return browser


def get_maximal_id() -> int:
    """
    Find maximal proposal id on page - the last proposal on the page is one with
    the highest id
    """
    logger.info("Retrieving maximal proposal ID")
    proposal_numbers = []
    for category in CATEGORIES:
        pages = get_proposal_page(urljoin(BASE_URL + "predlogi/", category))
        # last proposal have the highest id
        id_ = int(pages[0].rsplit("/", maxsplit=1)[1])
        logger.info(f"Page {category}, max ID: {id_}")
        proposal_numbers.append(id_)

    max_id = max(proposal_numbers)
    logger.info(f"Maximal overall id is {max_id}")
    return max_id


def get_proposal_page(category_url: str) -> List[str]:
    html = requests.get(category_url)
    soup = BeautifulSoup(html.text, "html.parser")
    uls = soup.findAll("ul", {"class": "sug-list"})
    assert len(uls) == 1
    links = uls[0].findAll("a", href=True)
    assert len(links) == 15
    return [a["href"] for a in links]


def get_author(soup: BeautifulSoup) -> str:
    return soup.findAll("div", {"class": "author"})[0].a.text


def get_title(soup: BeautifulSoup) -> str:
    return soup.findAll("div", {"class": "text"})[0].h2.text


def get_text(soup: BeautifulSoup) -> str:
    return "\n".join(
        p.text for p in soup.findAll("div", {"class": "text"})[0].findAll("p")
    )


def get_upvotes_downvotes(soup: BeautifulSoup) -> Tuple[int, int]:
    upvotes, downvotes = None, None
    up = soup.findAll("div", {"class": "vote1"})
    if len(up):
        upvotes = int(up[0].span.text.split()[0])
    do = soup.findAll("div", {"class": "vote2"})
    if do:
        downvotes = int(do[0].span.text.split()[0])
    return upvotes, downvotes


def get_dates(soup: BeautifulSoup, date_type: str) -> Optional[date]:
    date = soup.find("div", {"class": "status"}).ul.findAll(recursive=False)
    for d in date:
        if d.span.text == date_type:
            return datetime.strptime(d.time.text.strip(), "%d.%m.%Y").date()
    return None


def get_response(soup: BeautifulSoup) -> Optional[str]:
    response = None
    odziv = soup.find("div", {"id": "proposition-response"})
    if odziv:
        paragraphs = odziv.findAll(recursive=False)
        response = "\n".join(p.text for p in paragraphs)

    if not response:
        res = soup.find("div", {"id": "statusInfo"})
        if res:
            res = res.findChildren("p")
            response = "\n".join(p.text for p in res)

    return response


def get_proposal_type(soup: BeautifulSoup) -> str:
    return soup.find("h1").text.strip()


def get_number_comments(soup: BeautifulSoup) -> int:
    return int(soup.find("span", {"class": "ico3-7"}).text.split()[0])


def get_number_views(soup: BeautifulSoup) -> int:
    return int(soup.find("span", {"class": "ico3-4"}).text.split()[0])


def scrape_single_proposal(proposal_idx: int, browser: WebDriver) -> Optional[Dict]:
    """Scrape proposal with ID == proposal_idx"""
    start_t = time.time()
    url = urljoin(BASE_URL + "predlog/", str(proposal_idx))
    logger.info(f"Scrapping {url}")
    browser.get(url)

    html = browser.page_source
    if browser.current_url == "https://predlagam.vladi.si/":
        # ids with missing proposal throw user to the default site
        logger.info(f"Skipped {url}: missing proposal")
        return None
    soup = BeautifulSoup(html, "html.parser")
    if soup.findAll(text="404: Vsebina ne obstaja"):
        logger.info(f"Skipped {url}: content does not exist")
        return None

    try:
        # some rare proposals have completely different shape and no
        # meta information (e.g. prop 679)
        url = browser.current_url
        proposal_id = url.split("/")[-1]
        author = get_author(soup)
        title = get_title(soup)
        text = get_text(soup)
        upvotes, downvotes = get_upvotes_downvotes(soup)
        sent_date = get_dates(soup, "PREDLOG POSLAN")
        end_consideration_date = get_dates(soup, "KONEC OBRAVNAVE")
        response_due_date = get_dates(soup, "ROK ZA ODGOVOR")
        response_date = get_dates(soup, "ODGOVOR")
        response = get_response(soup)
        proposal_type = get_proposal_type(soup)
        number_comments = get_number_comments(soup)
        number_views = get_number_views(soup)
    except IndexError:
        logger.info(f"Skipped {url}: bad proposal format")
        return None

    logger.info(f"Scrapped {url} in {round(time.time() - start_t, 3)} seconds")

    return {
        "id": proposal_id,
        "url": url,
        "proposal type": proposal_type,
        "author": author,
        "title": title,
        "text": text,
        "upvotes": upvotes,
        "downvotes": downvotes,
        "response": response,
        "sent date": sent_date,
        "end consideration date": end_consideration_date,
        "response due date": response_due_date,
        "response date": response_date,
        "number comments": number_comments,
        "number views": number_views,
    }


def save_proposal(proposal: Dict):
    """Save proposal text in text file and meta information to yaml"""
    logger.info(f"Saving proposal with ID {proposal['id']} to file")
    dir_ = os.path.join(ROOT_DIRECTORY, DESTINATION_DIRECTORY)

    # save proposal text as txt file
    text_file = f"{proposal['id']}.txt"
    with open(os.path.join(dir_, text_file), "w") as f:
        f.write(proposal["text"])

    # save metainfo as yaml
    proposal = proposal.copy()
    proposal["Text file"] = text_file
    proposal.pop("text")

    with open(os.path.join(dir_, f"{proposal['id']}.yaml"), "w") as f:
        yaml.dump(proposal, f, default_flow_style=False)


def main():
    # prepare environment
    cleanup()
    init()
    # get maximal proposal id
    max_id = get_maximal_id()
    # init browser
    browser = init_browser()

    # retrieving proposals from the newest to the oldest
    proposals = []
    for i in range(max_id, 0, -1):
        proposal = scrape_single_proposal(i, browser)
        if proposal:
            save_proposal(proposal)
        proposals.append(proposal)
    browser.close()
    df = pd.DataFrame(proposals)
    df.to_csv(os.path.join(ROOT_DIRECTORY, CSV_FILE), index=False)


if __name__ == "__main__":
    main()
