"""
    Given a list of special files, looks for them and tries to parse them for metadata.
    Also supports yaml equivalents.

    Currently supported files:
        input_definition_data_schema.json / input_data_schema.json
        output_definition_data_schema.json / output_data_schema.json
        hyperparameter_schema.json
        hyperparameters.json
        input_trained_data_schema.json
        output_trained_data_schema.json
        features.json
        topology.json
        pipeline.json
"""

from .gh_utils import get_file_from_repo, merge_metadata, path_to_object

SPECIAL_FILES = {
    "input_definition_data_schema": "definition/input_data_schema",
    "input_data_schema": "definition/input_data_schema",
    "output_definition_data_schema": "definition/output_data_schema",
    "output_data_schema": "definition/output_data_schema",
    "hyperparameter_schema": "definition/hyperparameter_schema",
    "topology": "definition/topology",
    "hyperparameters": "training/hyperparameters",
    "features": "training/features",
    "input_trained_data_schema": "trained_model/input_data_schema",
    "output_trained_data_schema": "trained_model/output_data_schema",
    "pipeline": "pipeline"
}

def is_special_file(filename):
    for special_file_names in SPECIAL_FILES.keys():
        if filename.endswith(special_file_names + ".json") or filename.endswith(special_file_names + ".yaml"):
            return True
    return False

def get_special_file(repo_object, filepath, propertypath, metadata, is_yaml=False):
    contents = get_file_from_repo(repo_object, filepath)
    if contents is None:
        return metadata
    return path_to_object(metadata, contents, propertypath, to_object=True, is_yaml=is_yaml)

def detect_special_files(repo_object, tree_path=None):
    result = {}

    for k, v in SPECIAL_FILES.items():
        if tree_path:
            folders = "/".join(tree_path)
            json_file = folders + "/" + k + ".json"
            yaml_file = folders + "/" + k + ".yaml"
        else:
            json_file = k + ".json"
            yaml_file = k + ".yaml"
        path = v
        result = get_special_file(repo_object, json_file, path, result)
        result = get_special_file(repo_object, yaml_file, path, result, is_yaml=True)

    return result
