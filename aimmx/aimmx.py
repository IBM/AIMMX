from github3 import login, GitHubEnterprise, exceptions

from .util.gh_utils import merge_metadata, get_all_files_from_folder, get_blob_link, get_tree_link, get_file_from_repo, is_binary_ext
from .util.special_file_detector import detect_special_files, is_special_file
from .util.readme_cleanup import readme_cleanup
from .readme_parsers import readme_parse, readme_parse_text, get_readme_contents, get_readme_contents_from_path, is_readme_file, get_readme_contents_from_docstring
from .framework_detector.framework_detector import repo_framework
from .framework_detector.framework_extractor import extract_framework
from .dataset_detector.dataset_detector import detect_datasets_list
from .domain_inference.domain_inference import domain_inference
from .util.caffe2_utils import value_json_to_schema
import json

# aimmx client class
class AIMMX:
    """ Client for AIMMX."""

    def __init__(self, public_gh_token, enterprise_gh_creds=None):
        """

        """
        self._public_token = public_gh_token
        self._gh = login(token=public_gh_token)
        if enterprise_gh_creds:
            self._enterprise_login = enterprise_gh_creds[0]
            self._enterprise_token = enterprise_gh_creds[1]
            gh = GitHubEnterprise("https://github.ibm.com")
            self._gh_ent = gh.login(enterprise_gh_creds[0], password=enterprise_gh_creds[1])

    def repo_parse(self, repo_url):

        result = {}

        if "github.ibm.com" in repo_url:
            if not self._gh_ent:
                raise Exception("Must provide enterprise GitHub credentials to extract from enterprise repositories.")
            result["visibility"] = {
                "visibility": "private"
            }
            gh = self._gh_ent
        else:
            result["visibility"] = {
                "visibility": "public"
            }
            gh = self._gh

        s = repo_url.split("/")
        owner = s[3]
        repo_name = s[4]
        repo = gh.repository(owner, repo_name)

        print("Extracting AI model metadata from: ", repo)

        # check if the url given is a directory or single file
        branch = None
        tree_path = None
        blob_path = None
        if len(s) >= 8:
            branch = s[6]
            if s[5] == "tree":
                tree_path = s[7:]
            if s[5] == "blob":
                blob_path = s[7:]

        # NOTE: need preview accept header for topics, may be brittle
        gh.session.headers["Accept"] = "application/vnd.github.mercy-preview+json"

        result["name"] = repo.name
        result["definition"] = {
            "code": [{
                "type": "repo",
                "repo_type": "github",
                "owner": owner,
                "owner_type": repo.owner.as_dict()["type"],
                "name": repo_name,
                "url": repo_url,
                "stars": repo.stargazers_count,
                "pushed_at": str(repo.pushed_at),
                "created_at": str(repo.created_at),
                "language": repo.language
            }]
        }


        # Get all the files in the repo
        if not blob_path:
            files = get_all_files_from_folder(repo, tree_path=tree_path)
        else:
            # Single file case
            f = (blob_path[-1], "file", repo.file_contents("/".join(blob_path)))
            files = [f]
            tree_path = blob_path[:-1]
        blob_link = get_blob_link(repo, tree_path=tree_path, branch_name=branch)

        for f in files:
            if is_special_file(f[0]):
                continue
            if is_readme_file(f[0]):
                continue
            code_meta = {
                "type": "code",
                "name": f[0],
                "sha": f[2].sha,
                "filetype": f[1],
                "connection": {
                    "name": "github_url",
                    "source": {}
                }
            }
            if f[1] == "file":
                code_meta["size"] = f[2].size
                code_meta["connection"]["source"] = {"url": blob_link + "/" + f[0]}
            elif f[1] == "dir":
                code_meta["num_files"] = len(f[2].tree)
                code_meta["connection"]["source"] = {
                    "url": get_tree_link(repo, tree_path=tree_path, branch_name=branch) + "/" + f[0]
                }

            if is_binary_ext(f[0]):
                if "trained_model" not in result:
                    result["trained_model"] = {}
                    if "binaries" not in result["trained_model"]:
                        result["trained_model"]["binaries"] = []

                code_meta["type"] = "binary"
                result["trained_model"]["binaries"].append(code_meta)
            else:
                result["definition"]["code"].append(code_meta)

            # Caffe2 special case
            # NOTE: should later be refactored into a caffe2 specific portion
            if f[0] == "value_info.json":
                schema_contents = f[2].decoded
                input_schema = value_json_to_schema(schema_contents)
                if input_schema:
                    result["trained_model"]["input_data_schema"] = input_schema

        for c in repo.contributors():
            if "authors" not in result:
                result["authors"] = []
            user = gh.user(c.login)
            author = {}
            if (user.name and len(user.name) > 0):
                author["name"] = user.name
            else:
                author["name"] = c.login
            if (user.email and len(user.email) > 0):
                author["email"] = user.email
            author["github_id"] = c.login
            result["authors"].append(author)

        # Gets all the topics/tags in GitHub repo
        topics = repo.topics()
        if topics:
            result["tags"] = []
            for t in topics.names:
                result["tags"].append(t)

        repo_desc = None
        if repo.description:
            result["description"] = repo.description
            result["definition"]["code"][0]["description"] = repo.description
            repo_desc = repo.description

        extraction = {
            "type": "github",
            "url": repo_url,
            "stars": repo.stargazers_count,
            "issues": repo.has_issues
        }

        # Gets readme and does analysis
        readme_content = None
        # For single file case, treats docstring as the readme
        if blob_path:
            readme_content = get_readme_contents_from_docstring(repo, files[0][2].sha)
            if readme_content is not None:
                extraction["readme"] = readme_content
                extraction["readme_url"] = repo_url
        # Subfolder case and also if single file does not contain docstring
        if tree_path and (not blob_path or readme_content is None):
            readme_content = get_readme_contents_from_path(repo, tree_path)
            if readme_content is not None:
                extraction["readme"] = readme_content
                extraction["readme_url"] = repo_url
        # if subfolder case does not find a README, try with repo-level README
        if readme_content is None:
            readme_content = get_readme_contents(repo)
            if readme_content is not None:
                extraction["readme"] = readme_content
                extraction["readme_url"] = "/".join(s[:5])

        result["extraction"] = [extraction]

        repo_license = None
        try:
            if repo.license():
                repo_license = repo.license().license.name
                result["visibility"]["license"] = repo_license
                result["definition"]["code"][0]["license"] = repo_license
        except exceptions.NotFoundError:
            pass

        # outdated framework extraction
        # frameworks = repo_framework(repo)
        # if (frameworks and len(frameworks.keys()) > 0):
        #     result["definition"]["code"][0]["framework"] = []
        #     for fw,version in frameworks.items():
        #         fw_insert = {
        #             "name": fw
        #         }
        #         if version != "":
        #             fw_insert["version"] = version
        #         # NOTE: for now, framework is singular, change this later
        #         result["definition"]["code"][0]["framework"] = fw_insert

        readme_info = readme_parse(repo, branch_name=branch, check_datasets=True)
        readme_name = None
        if "name" in readme_info:
            readme_name = readme_info["name"]
        result = merge_metadata(result, readme_info)

        if tree_path:
            readme_info = readme_parse(repo, branch_name=branch, tree_path=tree_path, check_datasets=True)
            # special case for subfolders, if there's no other name, take it from the folder
            if "name" not in readme_info:
                readme_info["name"] = "/".join(tree_path)
            result = merge_metadata(result, readme_info)

        if blob_path:
            readme_info = readme_parse_text(readme_content, blob_link, check_datasets=True)
            result = merge_metadata(result, readme_info)

        # special case to add frameworks to code files
        if "definition" in result and "framework" in result["definition"]:
            if "code" in result["definition"]:
                result["definition"]["code"][0]["framework"] = {
                    "name": result["definition"].pop("framework")
                }

        # Special files check, doesn't make sense in single-file case
        if not blob_path:
            specialfiles = detect_special_files(repo, tree_path=tree_path)
            result = merge_metadata(result, specialfiles)

        # if README exists, attempt domain Inference and dataset detection
        if readme_content:
            plain_readme = readme_cleanup(readme_content)

            abstracts = ""
            if "references" in result:
                for r in result["references"]:
                    if "abstract" in r:
                        abstract = r["abstract"]
                        abstract = abstract.strip().replace("\n", " ")
                        abstracts +=  "\n{}".format(abstract)
            if len(abstracts) > 0:
                plain_readme += abstracts

            domain = domain_inference(plain_readme)
            result["domain"] = domain

            # NOTE: currently only running on abstracts, should refactor to run on abstract + readme
            abs_datasets = detect_datasets_list(abstracts)
            if len(abs_datasets) > 0:

                if "training" in result and "datasets" in result["training"]:
                    dataset_names = set()
                    datasets_to_add = []
                    for d in result["training"]["datasets"]:
                        dataset_names.add(d["name"].lower())
                    for d in abs_datasets:
                        if d["name"].lower() not in dataset_names:
                            datasets_to_add.append(d)
                    result["training"]["datasets"] += datasets_to_add
                else:
                    result["training"]["datasets"] = abs_datasets

        # attempt to extract framework via cloning
        framework_result = extract_framework(repo_url)
        if framework_result["success"]:
            if "frameworks" in framework_result:
                result["extraction"][0]["frameworks"] = framework_result["frameworks"]
                if "code" in result["definition"]:
                    result["definition"]["code"][0]["frameworks"] = framework_result["frameworks"]
            if "modules" in framework_result:
                result["extraction"][0]["modules"] = framework_result["modules"]
                if "code" in result["definition"]:
                    result["definition"]["code"][0]["modules"] = framework_result["modules"]

        return result
