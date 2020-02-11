"""
    Utility functions used by the various parsers.
"""

from github3.exceptions import NotFoundError
import base64, json, yaml

BINARY_EXTS = (".checkpoint", "Dockerfile", ".caffemodel", ".pb", ".pbtxt",
    ".prototxt", ".ckpt", ".meta", ".index", ".onnx", ".joblib", ",pkl", ".h5",
    ".hdf5", "value_info.json")

# Expects repo object from github.repo, returns None if not found
def get_file_from_repo(repo_object, filepath):
    file_contents = None
    try:
        file_contents = repo_object.file_contents(filepath)
    except NotFoundError as e:
        return None
    if file_contents is not None:
        #contents = file_contents.decoded
        contents = file_contents.content
        if file_contents.encoding == "base64":
            contents = base64.b64decode(contents)
            contents = contents.decode('UTF-8')
        return contents

# slightly more complicated dict merger that is subobject aware
# for conflicts, dict2 takes priority
def merge_metadata(dict1, dict2):
    SUBOBJECTS = ["definition", "training", "trained_model", "provenance"]
    result = {**dict1, **dict2}
    for s in SUBOBJECTS:
        if s in dict1 and s in dict2:
            result[s] = {**dict1[s], **dict2[s]}
            # check for inner dicts
            for k, v in dict1[s].items():
                if k in dict2[s] and isinstance(v, dict):
                    result[s][k] = {**dict1[s][k], **dict2[s][k]}
    # special case of evaluations
    if "evaluations" in dict1 and "evaluations" in dict2:
        result["evaluations"] = dict1["evaluations"]
        for ev in dict2["evaluations"]:
            result["evaluations"].append(ev)
    # special note of authors: 2nd dict takes priority in list order
    if "authors" in dict2 and "authors" in dict1:
        result["authors"] = dict1["authors"]
        for a in dict2["authors"]:
            result["authors"].append(a)
    if "trained_model" in dict1 and "trained_model" in dict2:
        if "binaries" in dict1["trained_model"] and "binaries" in dict2["trained_model"]:
            result["trained_model"]["binaries"] = dict1["trained_model"]["binaries"] + dict2["trained_model"]["binaries"]
    return result

def get_blob_link(repo_object, tree_path=None, branch_name=None):
    if not branch_name:
        branch = repo_object.default_branch
    else:
        branch = branch_name
    url = repo_object.html_url
    if tree_path:
        folders = "/".join(tree_path)
        url += "/blob/" + branch + "/" + folders
    else:
        url += "/blob/" + branch
    return url

def get_tree_link(repo_object, tree_path=None, branch_name=None):
    if not branch_name:
        branch = repo_object.default_branch
    else:
        branch = branch_name
    url = repo_object.html_url
    if tree_path:
        folders = "/".join(tree_path)
        url += "/tree/" + branch + "/" + folders
    else:
        url += "/tree/" + branch
    return url

# returns all files in folder in tuples of (path, type, blob/tree)
# NOTE: only the first tree (at least for now, due to performance reasons)
def get_all_files_from_folder(repo_object, tree_path=None, exceptions=[]):
    if tree_path:
        folder_name = "/".join(tree_path)
    else:
        folder_name = "/"
    contents = repo_object.directory_contents(folder_name)
    file_contents = []
    for c in contents:
        try:
            if c[1].type == "dir" and c[0] not in exceptions:
                file_contents.append( (c[0], "dir", repo_object.tree(c[1].sha)) )
            else:
                file_contents.append( (c[0], "file", repo_object.blob(c[1].sha)) )
        except NotFoundError as e:
            # NOTE: seems to trigger for submodules, for now, go ahead and skip
            print(e)
            continue
    return file_contents

# given path and metadata_object, traverses object and inserts value into path
# to_object converts the value into an object
def path_to_object(metadata_object, value, path, to_object=False, is_yaml=False):
    path_list = path.split("/")
    # ensure each object before the last part of the path is created
    current_object = metadata_object
    for i in range(len(path_list)):
        path_part = path_list[i]

        if i < len(path_list) - 1:
            if path_part not in current_object:
                current_object[path_part] = {}
            current_object = current_object[path_part]
        else:
            # last part path
            if to_object:
                if is_yaml:
                    value = yaml.safe_load(value)
                else:
                    value = json.loads(value)
            current_object[path_part] = value
    return metadata_object

def is_binary_ext(path):
    if path.endswith(BINARY_EXTS):
        return True
    return False
