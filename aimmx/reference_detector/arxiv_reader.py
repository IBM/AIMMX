"""
    Utility functions to lookup arxiv papers given a url or id
"""

import arxiv
import re
from dateutil import parser

# http://arxiv.org/abs/1502.05698
# https://arxiv.org/pdf/1512.03385.pdf

ARXIV_ABS_PATTERN = "https?:\/\/arxiv.org\/abs\/(\d+\.\d+)"
ARXIV_PDF_PATTERN = "https?:\/\/arxiv.org\/pdf\/(\d+\.\d+)\.pdf"
ARXIV_ID_PATTERN = "arXiv:(\d+\.\d+)"

# Given url, returns None if not arxiv or id if is
def parse_arxiv_url(url):
    arxiv_abs_re = re.compile(ARXIV_ABS_PATTERN)
    arxiv_pdf_re = re.compile(ARXIV_PDF_PATTERN)

    found = arxiv_abs_re.search(url)
    if found:
        return found.group(1)
    found = arxiv_pdf_re.search(url)
    if found:
        return found.group(1)

    return None

# Given full readme, look for arxiv and return info about each paper
def look_for_arxiv_fulltext(text):
    arxiv_abs_re = re.compile(ARXIV_ABS_PATTERN)
    arxiv_pdf_re = re.compile(ARXIV_PDF_PATTERN)

    ids = set()
    found = arxiv_abs_re.findall(text)
    if found and len(found) > 0:
        for f in found:
            ids.add(f)
    found = arxiv_pdf_re.findall(text)
    if found and len(found) > 0:
        for f in found:
            ids.add(f)

    paper_info = []
    for i in ids:
        paper_info.append(get_arxiv_id(i))
    return paper_info

# Given array of lines, look for arxiv and return info about each paper
def look_for_arxiv(lines, start=0, end=None):
    arxiv_abs_re = re.compile(ARXIV_ABS_PATTERN)
    arxiv_pdf_re = re.compile(ARXIV_PDF_PATTERN)

    if not end:
        end = len(lines)-1

    ids = set()
    for i in range(start,end+1):
        line = lines[i]
        #print(line)
        found = arxiv_abs_re.search(line)
        if found:
            ids.add(found.group(1))
        found = arxiv_pdf_re.search(line)
        if found:
            ids.add(found.group(1))

    paper_info = []
    for i in ids:
        paper_info.append(get_arxiv_id(i))
    return paper_info

# Given text, look for arxiv and return info about paper
def look_for_arxiv_id(text):
    arxiv_re = re.compile(ARXIV_ID_PATTERN)
    match = arxiv_re.search(text)
    if match:
        arxiv_id = match.group(1)
        arxiv_info = get_arxiv_id(arxiv_id)
        return arxiv_info
    return None

def get_arxiv_id(id):
    results = arxiv.query(id_list=[id])
    # assume one result
    if len(results) > 0:
        result = results[0]
        published = parser.parse(result.published)
        paper_info = {
            "title": result.title,
            "authors": result.authors,
            "arxiv": id,
            "year": published.year,
            "url": result.arxiv_url
        }
        if result.summary:
            paper_info["abstract"] = result.summary
    return paper_info
