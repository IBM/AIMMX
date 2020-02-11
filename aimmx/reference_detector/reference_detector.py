"""
    Given a README-style string, find references.
"""

from .arxiv_reader import look_for_arxiv_fulltext, parse_arxiv_url, look_for_arxiv_id
import re
import bibtexparser

REF_PATTERNS = {
    # IBM MAX 1, ex:* _S. Hershey, S. Chaudhuri, D. P. W. Ellis, J. F. Gemmeke, A. Jansen,\nR. C. Moore, M. Plakal, D. Platt, R. A. Saurous, B. Seybold et  al._,\n["CNN architectures for large-scale audio classification,"](https://arxiv.org/pdf/1609.09430.pdf) arXiv preprint\narXiv:1609.09430, 2016.
    '\* _([A-Za-z,\-\.\s]+?)_\s?,\s?\["?(.+?)"?\]\((\S+?)\)\s?arXiv preprint\s?(arXiv:\d+\.\d+), (\d+)\.': ["authors", "title", "url", "arxiv", "year"],
    # IBM MAX 2, ex:* _Qiuqiang Kong, Yong Xu, Wenwu Wang, Mark D. Plumbley_,["Audio Set classification with attention model: A probabilistic perspective."](https://arxiv.org/pdf/1711.00927.pdf) arXiv preprint arXiv:1711.00927 (2017).
    '\* _([A-Za-z,\-\.\s]+?)_\s?,\s?\["?(.+?)"?\]\((\S+?)\)\s?arXiv preprint\s?(arXiv:\d+\.\d+) \((\d+)\)\.': ["authors", "title", "url", "arxiv", "year"],
    # IBM MAX 3, ex:* _Jort F. Gemmeke, Daniel P. W. Ellis, Dylan Freedman, Aren Jansen, Wade Lawrence, R. Channing Moore, Manoj Plakal, Marvin Ritter_,["Audio set: An ontology and human-labeled dataset for audio events"](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/45857.pdf), IEEE ICASSP, 2017.
    '\* _([A-Za-z,\-\.\s]+?)_\s?,\s?\["?(.+?)"?\]\((\S+?)\)(?:\.|,) ([\s\S]+?), (\d+)\.': ["authors", "title", "url", "venue", "year"],
    # IBM MAX 4, ex:[1]<a name="ref1"></a> N. Shazeer, R. Doherty, C. Evans, C. Waterson., ["Swivel: Improving Embeddings\nby Noticing What's Missing"](https://arxiv.org/pdf/1602.02215.pdf) arXiv preprint arXiv:1602.02215 (2016)
    '\[\d+\]<a (?:.*)><\/a> ([A-Za-z,\-\.\s]+?)\s?\["?([\s\S]+?)"?\]\((\S+?)\)\s?arXiv preprint\s?(arXiv:\d+\.\d+) \((\d+)\)': ["authors", "title", "url", "arxiv", "year"],
    # IBM MAX 5, ex:[1] Jaderberg, Max, et al. ["Spatial Transformer Networks"](https://arxiv.org/pdf/1506.02025) arXiv preprint arXiv:1506.02025 (2015)
    '\[\d+\]\s?([A-Za-z,\-\.\s]+?)\s?\["?([\s\S]+?)"?\]\((\S+?)\)\s?arXiv preprint\s?(arXiv:\d+\.\d+) \((\d+)\)': ["authors", "title", "url", "arxiv", "year"],
    # IBM MAX 6, ex:* _D. Tran, L. Bourdev, R. Fergus, L. Torresani, M. Paluri_, [C3D: Generic Features for Video Analysis](http://vlg.cs.dartmouth.edu/c3d/)
    '\* _([A-Za-z,\-\.\s]+?)_\s?,\s?\["?(.+?)"?\]\((\S+?)\)': ["authors", "title", "url"],
    # IBM MAX 7, ex:* [Sports-1M Dataset Project Page](https://cs.stanford.edu/people/karpathy/deepvideo/)
    '\* \["?(.+?)"?\]\((\S+?)\)': ["title", "url"],
    # IBM MAX 8, ex: Rafal Jozefowicz, Oriol Vinyals, Mike Schuster, Noam Shazeer: “Exploring the Limits of Language Modeling”, 2016;\n[arXiv:1602.02410](http://arxiv.org/abs/1602.02410).
    '^([A-Za-z,\-\.\s]+?)\s?:\s?"?(.+?)"?, (\d+);\s?\["?(.+?)"?\]\((\S+?)\)\.': ["authors", "title", "year", "arxiv", "url"],
    # GitHub, ex:  - Raissi, Maziar, Paris Perdikaris, and George Em Karniadakis. "[Physics Informed Deep Learning (Part I): Data-driven Solutions of Nonlinear Partial Differential Equations](https://arxiv.org/abs/1711.10561)." arXiv preprint arXiv:1711.10561 (2017).
    '\s*?-\s?([A-Za-z,\-\.\s]+?).\s?"\["?(.+?)"?\]\((\S+?)\)."\s?arXiv preprint\s?(arXiv:\d+\.\d+)\s?\((\d+?)\)\.': ["authors", "title", "url", "arxiv", "year"],
}
URL_PATTERN = "^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"
URL_ENDER_EXCEPTIONS = (".json", ".yaml", ".py", ".ipynb")
ANCHOR_PATTERN = "^#\S+"
CODEBLOCK_PATTERN = "\s+?```(?:bibtex|)([\s\S]+?)```"

def make_paper_key(ref_info):
    title = ref_info["title"] if "title" in ref_info else ""
    authors = ""
    if "authors" in ref_info:
        if isinstance(ref_info["authors"], list):
            for a in ref_info["authors"]:
                authors += a
        elif isinstance(ref_info["authors"], str):
            authors = ref_info["authors"]
    return title + authors

def detect_references(readme):
    found = {}

    arxiv_ids = set()
    arxiv_papers = look_for_arxiv_fulltext(readme)
    for a in arxiv_papers:
        arxiv_ids.add(a["arxiv"])
        paper_key = make_paper_key(a)
        found[paper_key] = a

    bibtex_papers = codeblock_search(readme)
    for b in bibtex_papers:
        # skip if arxiv already found
        if "arxiv" in b:
            if b["arxiv"] in arxiv_ids:
                continue
            if "arxiv:" in b["arxiv"].lower():
                arxiv_id = b["arxiv"][b["arxiv"].lower().find("arxiv:")+len("arxiv:"):]
                if arxiv_id in arxiv_ids:
                    continue
        paper_key = make_paper_key(b)
        if paper_key not in found:
            found[paper_key] = b
        else:
            if len(b.keys()) > len(found[paper_key].keys()):
                found[paper_key] = b

    regex_papers = regex_search(readme)
    for r in regex_papers:
        # skip entire ref if arxiv already found
        if "arxiv" in r:
            if r["arxiv"] in arxiv_ids:
                continue
            if "arxiv:" in r["arxiv"].lower():
                arxiv_id = r["arxiv"][r["arxiv"].lower().find("arxiv:")+len("arxiv:"):]
                if arxiv_id in arxiv_ids:
                    continue
        if "url" in r:
            arxiv_id = parse_arxiv_url(r["url"])
            if arxiv_id and arxiv_id in arxiv_ids:
                continue
        paper_key = make_paper_key(r)
        # give priority to arxiv
        if paper_key not in found:
            found[paper_key] = r
        else:
            if len(r.keys()) > len(found[paper_key].keys()):
                found[paper_key] = r

        if len(found.values()) > 0:
            refs = []
            for ref in found.values():
                if "authors" in ref and isinstance(ref["authors"], str):
                    ref["authors"] = ref["authors"].split(",")
                refs.append(ref)
            return {
                "references": refs
            }

    return {}

def regex_search(readme):
    ref_res = []
    for r in REF_PATTERNS.keys():
        ref_res.append(re.compile(r, re.M))

    found_refs = []
    for r in ref_res:
        result = r.findall(readme)
        headers = REF_PATTERNS[r.pattern]
        for match in result:
            ref = {}
            for i in range(len(headers)):
                header = headers[i]
                ref[header] = match[i]
            if "url" in ref:
                # skip if not actual URL
                url_re = re.compile(URL_PATTERN)
                urls = url_re.search(ref["url"])
                if not urls:
                    continue
                # skip if URL ends with certain strings
                if ref["url"].endswith(URL_ENDER_EXCEPTIONS):
                    continue
            # skip entire ref if url is an anchor (i.e. just #)
                anchor_re = re.compile(ANCHOR_PATTERN)
                anchors = anchor_re.search(ref["url"])
                if anchors:
                    continue

            found_refs.append(ref)
    return found_refs

def codeblock_search(readme):
    found_refs = []
    codeblock_re = re.compile(CODEBLOCK_PATTERN, re.M)
    result = codeblock_re.findall(readme)
    for match in result:
        #print("regex match", match)
        bib_results = bibtexparser.loads(match)
        if len(bib_results.entries) > 0:
            for e in bib_results.entries:
                ref = bibtexparser.customization.author(e)
                ref["authors"] = ref["author"]
                if "journal" in ref:
                    arxiv_info = look_for_arxiv_id(ref["journal"])
                    if arxiv_info:
                        # merge, give preference to whatever is longer
                        for k,v in arxiv_info.items():
                            if k == "arxiv":
                                ref[k] = v
                            try:
                                if k in ref:
                                    if len(v) > len(ref[k]):
                                        ref[k] = v
                                    else:
                                        ref[k] = v
                            except TypeError:
                                ref[k] = v
                found_refs.append(ref)

    return found_refs
