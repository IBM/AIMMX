"""
    Utility functions for detecting datasets in a README file or similar
"""

import re
try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

LINK_PATTERN = "\[([^\]]+?)\]\(([^\)]+?)\)"
ANCHOR_PATTERN = "^#\S+"
BOUNDRY_PATTERN = "(\s|\W)?"

DATASET_LIST_PATH = "sota-datasets.csv"

def detect_datasets(readme, blob_link):
    dataset_list = load_dataset_list()
    datasets_found = []
    link_datasets = get_dataset_links(readme, blob_link)
    list_datasets = find_dataset_from_list(readme, dataset_list)
    datasets_found += link_datasets

    # resolve possible duplicates between the two, prioritize link datasets
    for list_dataset in list_datasets:
        skip = False
        for link_dataset in link_datasets:
            if list_dataset["name"].lower() in link_dataset["name"].lower():
                skip = True
                break
        if not skip:
            datasets_found.append(list_dataset)

    #print(datasets_found)
    return datasets_found

def load_dataset_list(dataset_list_path=DATASET_LIST_PATH):
    datasets = set()
    header = True
    with pkg_resources.open_text("aimmx", dataset_list_path) as f:
        for line in f:
            datasets.add(line.strip())
    return datasets

def find_dataset_from_list(readme, dataset_list):
    datasets_found = []
    for dataset in dataset_list:
        boundry_re = re.compile("(\W|\A)" + dataset.lower() + "(\W|\Z)", re.M)
        #print(boundry_re)
        #print(boundry_re.search(readme.lower()))
        if boundry_re.search(readme.lower()):
            d = {
                "name": dataset
            }
            datasets_found.append(d)
    return datasets_found

def get_dataset_links(readme, blob_link):
    link_re = re.compile(LINK_PATTERN)

    # extract out links and look for "dataset or data set" and an actual link
    matches = link_re.findall(readme)
    datasets = []
    if (matches and len(matches) > 0):
        for m in matches:
            if "dataset" in m[0].lower() or "data set" in m[0].lower() or "corpus" in m[0].lower():
                # ignore if anchor
                anchor_re = re.compile(ANCHOR_PATTERN)
                anchors = anchor_re.search(m[1])
                dataset = {}
                if anchors:
                    continue
                if "http" in m[1]:
                    dataset["name"] = m[0].strip()
                    dataset["connection"] = {
                        "name": "url",
                        "source": {
                            "url": m[1].strip()
                        }
                    }
                else:
                    # local link to file in repo
                    local_link = blob_link + "/" + m[1]
                    dataset["name"] = m[0].strip()
                    dataset["connection"] = {
                        "name": "url",
                        "source": {
                            "url": local_link
                        }
                    }
                datasets.append(dataset)
    return datasets

if __name__ == '__main__':
    print(detect_datasets("blah blah [mnist dataset](mnist) \n WMT2016 English-Romanian", ""))
