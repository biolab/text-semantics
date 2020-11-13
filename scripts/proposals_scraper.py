"""
This is a script for scraping proposals to government webpage predlagaj.valdi.si
Script scrapes all the proposals. And write them in the separate directory.
For every proposal it saves a .yaml file with metadata and separate files
with proposal texts, proposal, response (optinal - if response present),
and comments (optional - if comments present).

Requirements:
- requests,
- yaml,
- BeautifulSoup4,
- selenium,
- chromedriver_binary (from conda-forge) - chromium driver
"""

import os
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
import yaml
from bs4 import BeautifulSoup  # latest version bs4
from selenium import webdriver
# get from conda
try:
    import chromedriver_binary
except ImportError:
    print(f"Cannot import {chromedriver_binary}")
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.wait import WebDriverWait

BASE_URL = "https://predlagam.vladi.si/"
CATEGORIES = (
    "z-odzivom-organa",
    "zavrnjeni",
    "neustrezni",
    "zavrnjeni",
    "neustrezni",
)


def get_proposal_page(category_url):
    html = requests.get(category_url)
    soup = BeautifulSoup(html.text, "html.parser")
    uls = soup.findAll("ul", {"class": "sug-list"})
    assert len(uls) == 1
    links = uls[0].findAll("a", href=True)
    assert len(links) == 15
    return [a["href"] for a in links]


def get_author(soup):
    return soup.findAll("div", {"class": "author"})[0].a.text


def get_title(soup):
    return soup.findAll("div", {"class": "text"})[0].h2.text


def get_text(soup):
    return "\n".join(
        p.text for p in soup.findAll("div", {"class": "text"})[0].findAll("p")
    )


def get_upvotes_downvotes(soup):
    upvotes, downvotes = None, None
    up = soup.findAll("div", {"class": "vote1"})
    if len(up):
        upvotes = int(up[0].span.text.split()[0])
    do = soup.findAll("div", {"class": "vote2"})
    if do:
        downvotes = int(do[0].span.text.split()[0])
    return upvotes, downvotes


def get_dates(soup, date_type):
    date = soup.find("div", {"class": "status"}).ul.findAll(recursive=False)
    for d in date:
        if d.span.text == date_type:
            return datetime.strptime(d.time.text.strip(), "%d.%m.%Y").date()
    return None


def get_response(soup):
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


def get_proposal_type(soup):
    return soup.find("h1").text.strip()


def get_number_comments(soup):
    return int(soup.find("span", {"class": "ico3-7"}).text.split()[0])


def get_number_views(soup):
    return int(soup.find("span", {"class": "ico3-4"}).text.split()[0])


def get_comments(soup):
    comments = []
    cl = soup.find("ul", {"class": "comments-list"})
    if cl:
        lis = cl.findAll("section", {"class": "comment"})
        for c in lis:
            author = c.header.span.a.text
            content_div = c.findAll("div", recursive=False)
            comment_text = None  # only one match
            for d in content_div:
                if d.get("id").startswith("comment-body"):
                    comment_text = d.p.text
            assert comment_text is not None
            comments.append(f"---{author}---\n{comment_text}")
    return "\n".join(comments)


def scrape_single_proposal(proposal_url, browser):
    browser.get(proposal_url)
    # todo: handle comments
    # WebDriverWait(browser, 3).until_not(
    #     EC.text_to_be_present_in_element((By.ID, "comments"), "Nalagam ...")
    # )
    html = browser.page_source
    if browser.current_url == "https://predlagam.vladi.si/":
        # ids with missing proposal throw user to the default site
        return None
    soup = BeautifulSoup(html, "html.parser")
    if soup.findAll(text="404: Vsebina ne obstaja"):
        return None

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
    # comments = get_comments(soup)

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
        # "comments": comments,
    }


def save_proposal(proposal, prop_dir):
    # proposal is saved as a text file
    text_file = f"{proposal['id']}.txt"
    with open(os.path.join(prop_dir, text_file), "w") as f:
        f.write(proposal["text"])

    response_file = None
    if proposal["response"]:
        response_file = f"{proposal['id']}-response.txt"
        with open(os.path.join(prop_dir, response_file), "w") as f:
            f.write(proposal["response"])

    comment_file = None
    if proposal.get("comments"):
        comment_file = f"{proposal['id']}-comments.txt"
        with open(os.path.join(prop_dir, comment_file), "w") as f:
            f.write(proposal["comments"])

    proposal = proposal.copy()
    proposal["text"] = text_file
    proposal["response"] = response_file
    # proposal["comments"] = comment_file

    with open(os.path.join(prop_dir, f"{proposal['id']}.yaml"), "w") as f:
        yaml.dump(proposal, f, default_flow_style=False)


def main(chromium_driver_path):
    print("---Getting max id---")
    # find maximal proposal id on page - the last proposal on the page
    # is one with the highest id
    proposal_numbers = []
    for category in CATEGORIES:
        pages = get_proposal_page(urljoin(BASE_URL + "predlogi/", category))
        # last proposal have the highest id
        proposal_numbers.append(int(pages[0].rsplit("/", maxsplit=1)[1]))

    max_id = max(proposal_numbers)
    print("The maximum proposal id is ", max_id)

    # scrape all proposal starting with the max_id and continuing to zero
    proposals_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "proposals-to-government"
    )
    if not os.path.isdir(proposals_dir):
        os.mkdir(proposals_dir)

    print("---Scrapping---")
    # kwargs = [chromium_driver_path] if chromium_driver_path else []
    op = webdriver.ChromeOptions()
    op.add_argument('headless')
    browser = webdriver.Chrome(options=op)
    for i in range(max_id, 0, -1):
        t = time.time()
        url = urljoin(BASE_URL + "predlog/", str(i))
        try:
            # some rare proposals have completely different shape and no
            # meta information (e.g. prop 679)
            proposal = scrape_single_proposal(url, browser)
        except IndexError:
            # skip those
            proposal = None
            print(f"Skipping proposal {i}")

        if proposal:
            save_proposal(proposal, proposals_dir)
        print(f"Required {time.time() - t} for {url}")
        if i % 100 == 0:
            time.sleep(30)
    browser.close()


if __name__ == "__main__":
    driver_path = None if len(sys.argv) < 2 else sys.argv[1]
    main(driver_path)
