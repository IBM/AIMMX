"""
    Given a GitHub repo, extracts the readme and tries to find useful information
"""

from github3.exceptions import NotFoundError
import base64, re
from .reference_detector.arxiv_reader import look_for_arxiv_fulltext, parse_arxiv_url
from .util.gh_utils import merge_metadata, path_to_object, get_file_from_repo, get_blob_link
from .dataset_detector.dataset_detector import detect_datasets
from .reference_detector.reference_detector import detect_references

LINK_PATTERN = "\[([^\]]+?)\]\(([^\)]+?)\)"
ANCHOR_PATTERN = "^#\S+"

MODEL_HEADER_PATTERN = "## Model(?:s| Metadata)\s+?([\s\S]+?)\s+?(?:#|\Z)"
MODEL_VALUE_HEADER_PATTERN = "##\s+?Model Value\n+?((?:###\s+?(?:[^#]+?)\n(?:^\|[\S\s]+?\|\n{2,}))*)"
TABLE_PATTERN = "###\s+?([^#]+?)\n(^\|[\S\s]+?\|\n{2,})"

MODEL_METRIC_SPECIAL_CASE = "Test Set"

SCHEMA_HEADER_PATTERN_PRE = "##\s*?"
SCHEMA_HEADER_PATTERN_POST = "\s+?```(?:json|)([\s\S]+?)```"

TABLE_HEADER_PATTERN_PRE = "##\s*?"
TABLE_HEADER_PATTERN_POST = "\s+?(^\|[\S\s]+?\|\n{2,})"

CODE_BLOCK_HEADERS_DICT = {
    "Input(?: Definition| ) Data Schema": "definition/input_data_schema",
    "Output(?: Definition| ) Data Schema": "definition/output_data_schema",
    "Hyperparameter Schema": "definition/hyperparameter_schema",
    "Input Trained Data Schema": "trained_model/input_data_schema",
    "Output Trained Data Schema": "trained_model/output_data_schema"
}

README_FILES = ["README.md", "README", "readme.md", "readme"]
#INPUT_TRAINED_SCHEMA_HEADER = "## Input Trained Data Schema\s+?```(?:json)([\s\S]+?)```\s+?(?:#|\Z)"

def is_readme_file(filename):
    for readme_file_names in README_FILES:
        if filename.endswith(readme_file_names):
            return True
    return False

def get_readme_contents(repo_object):
    try:
        readme = repo_object.readme()
    except NotFoundError as e:
        return None
    contents = readme.content
    if readme.encoding == "base64":
        contents = base64.b64decode(contents)
        contents = contents.decode('UTF-8')
    return contents

def get_readme_contents_from_sha(repo_object, sha):
    readme_blob = repo_object.blob(readme_sha)
    readme = readme_blob.decode_content()
    return readme

def get_readme_contents_from_path(repo_object, tree_path):
    full_path = ""
    for folder in tree_path:
        full_path += folder +"/"
    readme = None
    for readme_names in README_FILES:
        readme_path = full_path + readme_names
        readme = get_file_from_repo(repo_object, readme_path)
        if readme:
            break
    return readme

def get_readme_contents_from_docstring(repo_object, sha):
    code_blob = repo_object.blob(sha)
    code = code_blob.decode_content()
    # only read the docstring ('''....''')
    start = None
    end = None
    lines = code.split("\n")
    for i in range(len(lines)):
        line = lines[i]
        #print(line)
        if line.startswith("'''") or line.startswith('"""'):
            if start is None:
                start = i
            elif end is None:
                end = i
                break
    if start is None or end is None:
        return None
    docstring = ""
    for i in range(start,end+1):
        line = lines[i].strip()
        # remove start of docstring
        if i == start:
            docstring_start = line.find("'''")
            if docstring_start == -1:
                docstring_start = line.find('"""')
            line = line[docstring_start+3:]
        # remove end of docstring
        if i == end:
            docstring_end = line.find("'''")
            if docstring_end == -1:
                docstring_end = line.find('"""')
            line = line[:docstring_end]
        docstring += line + "\n"
    return docstring

def get_readme_title(readme):
    link_re = re.compile(LINK_PATTERN)

    # Use readme title as model name
    lines = readme.splitlines()
    line_index = 0
    title = None
    while line_index < len(lines):
        line = lines[line_index].strip()
        skip = False

        if line == "":
            skip = True

        # skip cases
        if line.lower() == "introduction" or line.lower().startswith("*"):
            skip = True

        # special cases
        if "travis-ci" in line.lower():
            skip = True

        # special RST cases
        if line.lower().startswith(".. ") or line.lower().startswith(":target:"):
            skip = True

        # another special RST case
        rst_table_re = re.compile("^(\|[^\|]+?\|_\s*)+")
        matches = rst_table_re.search(line)
        if matches:
            skip = True

        # skip if line is a link and image
        link_image_re = re.compile("^\[!\[([^\]]+?)\]\(([^\)]+?)\)\]\(([^\)]+?)\)")
        matches = link_image_re.search(line)
        if matches:
            skip = True

        # skip if line is an Image
        image_re = re.compile("^!\[([^\]]+?)\]\(([^\)]+?)\)")
        matches = image_re.search(line)
        if matches:
            skip = True

        # skip if line is nothing but "-" or "=" or "*" or "_"
        lines_re = re.compile("^[-=\*_]+")
        matches = lines_re.search(line)
        if matches:
            skip = True

        if not skip:
            title = line
            # remove hashes in front and/or back if they exist
            title_re = re.compile("^#+ ([^#]+)#*$")
            matches = title_re.search(title)
            if (matches):
                title = matches.group(1).strip()

            # remove <tags> if they exist
            tags_re = re.compile("<[\S\s]+?>")
            matches = tags_re.findall(title)
            if (matches and len(matches) > 0):
                for m in matches:
                    title = title.replace(m, "")

            # if a link is in the title, replace it
            links = link_re.search(title)
            if links:
                title = title.replace(links.group(0), links.group(1))

            break

        line_index += 1

    return title

def get_dataset_links(readme, blob_link):
    link_re = re.compile(LINK_PATTERN)

    # extract out links and look for "dataset or data set" and an actual link
    matches = link_re.findall(readme)
    datasets = {}
    if (matches and len(matches) > 0):
        for m in matches:
            if "dataset" in m[0].lower() or "data set" in m[0].lower() or "corpus" in m[0].lower():
                # ignore if anchor
                anchor_re = re.compile(ANCHOR_PATTERN)
                anchors = anchor_re.search(m[1])
                if anchors:
                    continue
                if "http" in m[1]:
                    datasets[m[0]] = m[1]
                else:
                    # local link to file in repo
                    local_link = blob_link + "/" + m[1]
                    datasets[m[0]] = local_link
    return datasets

def check_codeblock(readme, header, metadata_path, metadata, to_object=False):
    header_pattern = SCHEMA_HEADER_PATTERN_PRE + header + SCHEMA_HEADER_PATTERN_POST
    header_re = re.compile(header_pattern, re.M | re.I)

    result = header_re.search(readme)
    if (result and len(result.groups()) > 0):
        code_block = result.group(1).strip()
        block_result = path_to_object({}, code_block, metadata_path, to_object)
        return merge_metadata(metadata, block_result)

    return metadata

def check_table(readme, header, metadata_path, metadata, header_value_dict=None):
    header_pattern = TABLE_HEADER_PATTERN_PRE + header + TABLE_HEADER_PATTERN_POST
    header_re = re.compile(header_pattern, re.M | re.I)

    result = header_re.search(readme)
    if (result and len(result.groups()) > 0):
        table_block = result.group(1).strip()
        table_result = parse_markdown_table(table_block, header_value_dict)
        if len(table_result) > 0:
            table_result = path_to_object(metadata, table_result, metadata_path)
        return table_result

    return metadata

# returns array of objects, optionally can define paths
def parse_markdown_table(metric_table_md, header_value_dict=None):
    rows = metric_table_md.split("\n")
    headers = rows[0].split("|")
    metadata_objects = []
    for r_index in range(2, len(rows)):
        metadata = None
        values = rows[r_index].split("|")
        for i in range(len(headers)):
            h = headers[i].strip()
            v = values[i].strip()

            if len(h) > 0:
                if not metadata:
                    metadata = {}
                if header_value_dict:
                    if h.lower() in header_value_dict:
                        metadata = path_to_object(metadata, v, header_value_dict[h.lower()])
                else:
                    metadata[h.lower()] = v

        if metadata:
            metadata_objects.append(metadata)

    return metadata_objects

def check_model_value_table(readme):
    metadata = {}
    header_re = re.compile(MODEL_VALUE_HEADER_PATTERN, re.M | re.I)
    result = header_re.search(readme)
    evaluations = []
    if (result and len(result.groups()) > 0):
        # add newlines for the regex pattern matching
        raw_table = result.group(1).strip() + "\n\n"
        table_re = re.compile(TABLE_PATTERN, re.M | re.I)
        results = table_re.findall(raw_table)
        metric_metadata = {
            "evaluation_type": "training_evaluation",
            "method": MODEL_METRIC_SPECIAL_CASE
        }
        metrics = []
        for r in results:
            metric_name = r[0]
            table_md = r[1].strip()
            parse_result = {
                "metric": metric_name,
            }
            # special case
            if metric_name.lower() == "cost of training":
                parse_result = parse_markdown_table(table_md)
                if len(parse_result) > 0:
                    metadata["training"] = {
                        "training_job": {
                            "costs": parse_result
                        }
                    }
            else:
                parse_results = parse_markdown_table(table_md)
                comparisons = []
                for pr in parse_results:
                    # special case that defines what the metric is
                    if "above" in pr and pr["above"].lower() == MODEL_METRIC_SPECIAL_CASE.lower():
                        parse_result["value"] = pr["measurement"]
                    else:
                        comparisons.append(pr)
                if len(comparisons) > 0:
                    parse_result["comparisons"] = comparisons
                metrics.append(parse_result)
        if len(metrics) > 0:
            metric_metadata["metrics"] = metrics

        evaluations.append(metric_metadata)
    if len(evaluations) > 0:
        metadata["evaluations"] = evaluations
    return metadata

def check_model_metadata_table(readme):
    metadata = { "domain": {} }
    header_re = re.compile(MODEL_HEADER_PATTERN, re.M | re.I)
    result = header_re.search(readme)
    if (result and len(result.groups()) > 0):
        raw_table = result.group(1).strip()
        rows = raw_table.split("\n")
        headers = rows[0].split("|")
        values = rows[2].split("|")
        for i in range(len(headers)):
            h = headers[i].strip()
            v = values[i].strip()

            if h == "Domain":
                metadata["domain"]["domain_type"] = v
            elif h == "Application":
                metadata["domain"]["tasks"] = [v]
            elif h == "Industry":
                metadata["domain"]["industries"] = [v]
            elif h == "Training Data" or h == "Datasets":
                # check if it's a link
                link_re = re.compile(LINK_PATTERN)
                matches = link_re.findall(v)
                datasets = []
                if (matches and len(matches) > 0):
                    for m in matches:
                        datasets.append({
                            "name": m[0],
                            "url": m[1]
                        })
                else:
                    datasets.append({
                        "name": v
                    })

                metadata["training"] = {
                    "datasets": datasets
                }
            elif h == "Input Data Format":
                if "definition" not in metadata:
                    metadata["definition"] = {}
                if "input_data_schema" not in metadata:
                    metadata["definition"]["input_data_schema"] = {}
                metadata["definition"]["input_data_schema"]["description"] = v
            elif h == "Framework":
                if "definition" not in metadata:
                    metadata["definition"] = {}
                metadata["definition"]["framework"] = v

    if len(metadata["domain"].keys()) == 0:
        del metadata["domain"]

    return metadata

def readme_parse_text(readme, blob_link, check_datasets=False):
    #refs = check_readme_refs(readme)
    refs = detect_references(readme)
    metadata = check_model_metadata_table(readme)
    #print(refs)
    result = merge_metadata(refs, metadata)

    metadata = check_model_value_table(readme)
    result = merge_metadata(result, metadata)

    author_header_dict = {
        "name": "name",
        "email": "email",
        "Github Profile": "github_id",
        "organization": "organization"
    }
    result = check_table(readme, "Contributors", "authors", result, author_header_dict)

    # check for special codeblocks
    for header, path in CODE_BLOCK_HEADERS_DICT.items():
        result = check_codeblock(readme, header, path, result, to_object=True)

    # special case of a codeblock containing published docker image address
    docker_result = check_codeblock(readme, "Published Docker Image:", "trained_model/binaries", {})
    if "trained_model" in docker_result and "binaries" in docker_result["trained_model"]:
        docker_address = docker_result["trained_model"]["binaries"]
        docker_result["trained_model"]["binaries"] = [{
            "name": "Published Docker Image",
            "type": "docker",
            "description": "URL to a docker repository where docker image is published",
            "connection": {
                "name": "docker_url",
                "source": {
                    "url": docker_address
                }
            }
        }]
        result = merge_metadata(result, docker_result)

    title = get_readme_title(readme)
    if title:
        result["name"] = title

    if check_datasets:
        datasets = detect_datasets(readme, blob_link)
        if len(datasets) > 0:
            if "training" not in result:
                result["training"] = {
                    "datasets": []
                }
            if "datasets" not in result["training"]:
                result["training"]["datasets"] = []
            for d in datasets:
                result["training"]["datasets"].append(d)

    return result


def readme_parse(repo_object, branch_name=None, tree_path=None, check_datasets=False):
    result = {}
    blob_link = get_blob_link(repo_object, tree_path=tree_path, branch_name=branch_name)
    if not tree_path:
        readme = get_readme_contents(repo_object)
    else:
        readme = get_readme_contents_from_path(repo_object, tree_path)

    if not readme:
        return result

    return readme_parse_text(readme, blob_link, check_datasets)
