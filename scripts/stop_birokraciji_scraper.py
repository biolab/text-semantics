from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.stopbirokraciji.gov.si/"
CATEGORIES = (
    "dispatched",
    "replied",
    "concluded",
)


def get_max_id_page(category):
    html = requests.get(urljoin(BASE_URL, f"pobude/?status_id={category}"))
    soup = BeautifulSoup(html.text, "html.parser")
    cards = soup.findAll("div", {"class": "card"})
    return max(int(c.div.a["href"].split("pobuda/?st=")[1]) for c in cards)


def get_max_id():
    """
    Find maximal proposal id on page - the last proposal on the page
    is one with the highest id
    """
    print("---Getting max id---")
    return max(get_max_id_page(category) for category in CATEGORIES)


def get_comment_data(soup, class_):
    comment = soup.find("div", {"class", class_})
    return (
        comment.find("span", {"class", "comment-data-value"}).text.strip()
        if comment
        else None
    )


def get_timeline(soup, class_):
    tml = soup.find("li", {"class": class_})
    return datetime.strptime(tml.span.span.text, "%d. %m. %Y") if tml else None


def get_ezu(soup):
    ezu = soup.find("li", {"class": "ezu"})
    if ezu:
        return datetime.strptime(ezu.a.span.text, "%d. %m. %Y"), ezu.a["href"]
    return None, None

def get_response(soup):
    resp = soup.find("div", {"class": "comment-reply"})
    return resp.text if resp else None

def get_proposal(soup):
    return "\n".join(t.text for t in soup.find("div", {"class": "comment-content"}))

def proposal_exists(soup):
    content = soup.find("div", {"class": "comment-content"})
    return (
        content.h3 is None or content.h3.text.strip() != "Pobuda uporabnika ne obstaja."
    )


def srap_single_page(page_id):
    url = urljoin(BASE_URL, f"pobuda/?st={page_id}")
    print(url)
    html = requests.get(url)
    soup = BeautifulSoup(html.text, "html.parser")
    if not proposal_exists(soup):
        print("not existing")
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


def scrape_pages(max_id):
    print("---Scrapping pages---")
    data = []
    for id_ in range(1, max_id + 1):
        proposal = srap_single_page(id_)
        if proposal is not None:
            data.append(proposal)
            print(data[-1])
    return pd.DataFrame(data)


def main():
    max_id = get_max_id()
    print("Max id:", max_id)

    df = scrape_pages(max_id)
    df.to_csv("stop-birokraciji.csv",index=False)


if __name__ == "__main__":
    main()
