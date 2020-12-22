import os
import pickle

import requests
from bs4 import BeautifulSoup


base_url = "https://ojs.inz.si/pnz/issue/view/{issue}"  # issue 1 - 22


def get_all_articles():
    # get articles
    articles = []
    for issue in range(1, 23):
        result = requests.get(base_url.format(issue=issue))
        soup = BeautifulSoup(result.content, 'lxml')
        if not any(x.text.strip() == "Articles" for x in soup.findAll("h2")):
            print(f"No issue {issue}")
            continue
        # find section with articles inside
        sections = [
            s for s in soup.findAll("div", attrs={"class": "section"})
            if any(x.text.strip() == "Articles" for x in s.findAll("h2"))
        ]
        assert len(sections) == 1

        for li in sections[0].ul.findAll("li", recursive=False):
            div = li.find("div", attrs={"class", "obj_article_summary"})
            ul = div.ul
            if any(x for x in ul.findAll("a") if x.text.strip() == "PDF (Slovenščina)"):
                files = ul.findAll("a", attrs={"class": "file"})
                file = [x['href'] for x in files if x.text.strip() in ("HTML", "HTML (Slovenščina)")]
                if file:
                    articles.append(file[0])
        print(f"issue {issue}", len(articles))
    return articles


if os.path.isfile("articles.pkl"):
    with open("articles.pkl", "rb") as f:
        articles = pickle.load(f)
else:
    articles = get_all_articles()
    with open("articles.pkl", "wb") as f:
        pickle.dump(articles, f)


def get_title(soup):
    title = soup.find("h2", attrs={"class": "maintitle"})
    return title.text.replace("*", "")


def get_abstract(soup):
    abstract = soup.find("section", attrs={"class": "abstract"})
    abstract = "\n".join(
        s.text for p in abstract.findAll("p")
        for s in p.findAll("span")
        if "numberParagraph" not in s.get("class", "")
        and "Ključne besede:" not in s.text
    )
    return abstract


def get_keywords(soup):
    abstract = soup.find("section", attrs={"class": "abstract"})
    kw = [
        s.text for p in abstract.findAll("p")
        for s in p.findAll("span")
        if "Ključne besede:" in s.text
    ]
    assert len(kw) == 1
    return kw[0].replace("Ključne besede: ", "").split(", ")


def read_articles(articles):
    for art in articles:
        print(art)
        result = requests.get(art)
        soup = BeautifulSoup(result.content, 'lxml')
        url = soup.find("iframe")["src"]
        result = requests.get(url)
        soup = BeautifulSoup(result.content, 'lxml')
        title = get_title(soup)
        abstract = get_abstract(soup)
        keywords = get_keywords(soup)
        print(keywords)




read_articles(articles[:1])