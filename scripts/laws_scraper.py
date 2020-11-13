"""
Script for parsing laws from PISRS and uradni list.

Requirements:
- BeautifulSoup
- pandas
"""

import os
import re
from datetime import datetime
from urllib.request import urlopen

import pandas as pd
from bs4 import BeautifulSoup as Soup

query = "register%20OR%20registr*"
web = "http://pisrs.si/Pis.web/"
filter_ = "zakoni"
save_to = "laws/"


def get_text(soup):
    return "\n".join(
        a.text
        for a in soup.findAll(True, {"class": ["esegment_h4", "esegment_p"]})
    )


def get_title(soup):
    return soup.find("h2", {"class": "h5 ul-content-title " "pull-left"}).text


def get_uradni_list_data(s):
    data = s.find("div", {"class": "slider-item--ul-issue-text__content"}).text
    match = re.search("Uradni list RS, št. (.*?) z dne (.*?)$", data)
    date = datetime.strptime(match.group(2).strip(), "%d. %m. %Y").date()
    return match.group(1), date


def scrape_single_uradni_list(url):
    """
    Scrape a single law uradni list
    """
    print("Scraping: ", url)
    zakon = urlopen(url)
    soup = Soup(zakon.read(), "html.parser")
    if not soup.find("h2", {"class": "h5 ul-content-title " "pull-left"}):
        return None
    title = get_title(soup)
    text = get_text(soup)
    issue, date_published = get_uradni_list_data(soup)

    t_short = (
        title[:100]
        .strip(".")
        .replace(" ", "-")
        .replace("/", "-")
        .replace(",", "")
    )
    text_file = f"{t_short}.txt"
    with open(f"{save_to}{text_file}", "w") as f:
        f.write(text)

    return {
        "Title": title,
        "Uradni list Issue": issue,
        "Date published": date_published,
        "Law text": text_file,
    }


def get_dates_passed_start(soup):
    dates = (
        soup.find("table", id="datumi")
        .find("table")
        .find("table")
        .findAll("tr")
    )
    date_passed = date_valid = None
    for r in dates:
        tds = r.findAll("td")
        if len(tds) > 0:
            if tds[0].text.strip() == "Datum sprejetja":
                date_passed = datetime.strptime(
                    tds[1].text.strip(), "%d.%m.%Y"
                ).date()
            if tds[0].text.strip() == "Datum začetka veljavnosti":
                date_valid = datetime.strptime(
                    tds[1].text.strip(), "%d.%m.%Y"
                ).date()
    return date_passed, date_valid


def get_institutions(soup):
    trs = soup.find("div", id="organi").findAll("tr")
    institution_accepted = institution_prepared = None
    for r in trs:
        tds = r.findAll("td")
        if tds[0].span.text.strip() == "Organ, ki je sprejel ta predpis":
            institution_accepted = tds[1].find("span").text.strip()
        if (
            tds[0].span.text.strip()
            == "Organi, odgovorni za pripravo tega predpisa"
        ):
            institution_prepared = tds[1].find("span").text.strip()
    return institution_accepted, institution_prepared


def scrape_single_law(link):
    """
    Open a single law and find a link to uradni list. If not existing skip
    """
    print(link)
    z_html = urlopen(link)
    s = Soup(z_html.read(), "html.parser")
    if not s.find(id="citatStrokAnali").find("a", href=True):
        return None
    md = scrape_single_uradni_list(
        s.find(id="citatStrokAnali").find("a", href=True)["href"]
    )
    if md is None:
        return None
    md["Date passed"], md["Date valid"] = get_dates_passed_start(s)
    md["Institution accepted"], md["Institution prepared"] = get_institutions(s)
    return md


def write_metadata(meta_data):
    v = {k: [dic[k] for dic in meta_data] for k in meta_data[0]}
    pd.DataFrame(v).to_csv(os.path.join(save_to, "metadata.csv"), index=False)


def main():
    if not os.path.exists(save_to):
        os.makedirs(save_to)

    page = 1
    meta_data = []
    while True:
        print("Scraping page", page)
        # open all pages with law lists
        html = urlopen(
            f"{web}pravniRedRSSearch?search="
            f"{query}&filter="
            f"{filter_}&chosenFilters=vsiPredpisi&od=&do=&sortOrder"
            f"=relevantnost&page={str(page)}&scrollTop=0"
        )
        print(f"{web}pravniRedRSSearch?search="
            f"{query}&filter="
            f"{filter_}&chosenFilters=vsiPredpisi&od=&do=&sortOrder"
            f"=relevantnost&page={str(page)}&scrollTop=0")
        s1 = Soup(html.read(), "html.parser")
        if s1.find(id="predpisi").find("a"):
            for a in s1.find(id="predpisiTable").find_all("a", href=True):
                res = scrape_single_law(f"{web}{a['href']}")
                if res:
                    meta_data.append(res)
                else:
                    print("skipped")
            page += 1
        else:
            break

    write_metadata(meta_data)


if __name__ == "__main__":
    main()
