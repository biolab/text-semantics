import io
import os
import re
import tempfile
from typing import List, Tuple, Any, Callable
from urllib.parse import urljoin, unquote

import docx2txt
import requests
from bs4 import BeautifulSoup
from odf import opendocument, text, teletype
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTTextLine


def parse_pdf(response):
    fp = io.StringIO(response.text)
    parser = PDFParser(fp)
    doc = PDFDocument()
    parser.set_document(doc)
    doc.set_parser(parser)
    doc.initialize("")
    rsrcmgr = PDFResourceManager()
    laparams = LAParams()
    laparams.char_margin = 1.0
    laparams.word_margin = 1.0
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    extracted_text = ""

    for page in doc.get_pages():
        interpreter.process_page(page)
        layout = device.get_result()
        for lt_obj in layout:
            if isinstance(lt_obj, LTTextBox) or isinstance(lt_obj, LTTextLine):
                extracted_text += lt_obj.get_text()
    return extracted_text


def parse_docx(response):
    tmp = tempfile.NamedTemporaryFile()
    with open(tmp.name, "wb") as f:
        f.write(response.content)

    return docx2txt.process(tmp.name)


def parse_odt(response):
    tmp = tempfile.NamedTemporaryFile()
    with open(tmp.name, "wb") as f:
        f.write(response.content)

    odtfile = opendocument.load(tmp.name)
    texts = odtfile.getElementsByType(text.P)
    return " ".join(teletype.extractText(t) for t in texts)


def list_files(url: str) -> List[Tuple[str, str]]:
    """
    Return a list of (filename, file-URL) pairs in the server directory
    """
    if not url.endswith("/"):
        url += "/"

    soup = BeautifulSoup(requests.get(url).text, "html.parser")
    return [
        (
            unquote(os.path.basename(node.get("href").rstrip("/"))),
            urljoin(url, node.get("href")),
        )
        for node in soup.find_all("a")
        if node.text != "../"
    ]


def natural_sorted(l: List[Any], key: Callable = lambda x: x):
    def convert(text: str):
        return int(text) if text.isdigit() else text.lower()

    def alphanum_key(items: Any):
        return [convert(c) for c in re.split("([0-9]+)", key(items))]

    return sorted(l, key=alphanum_key)
