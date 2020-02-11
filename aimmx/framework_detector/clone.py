import os
import fnmatch
import tempfile
import re
import json
from git import Repo

def extract_modules(text):
    importsRegEx = r"(?:import|from) ([\w\-]+)((?:(,\s*))[\w\-]+)*\s*(?:\s+as\s+\w*)?(?:import\s\w*)?[\n.]"
    # importsRegEx = r"(?:from|import)\s+(\w+)(?:\s+as\s+\w*)?[\n.]"
    mods = re.findall(importsRegEx, text)
    # return mods
    # if len(mods) > 0:
    #     print(text, " --- ", mods)
    modules = []
    for imp in mods:
        for i in imp:
            if len(i.strip()) > 0:
                modules.append(i.replace(",","").strip())
    # # print(modules)
    return modules

def get_py_modules(org, repo, repoPath=""):
    # TODO implement directory
    # TODO implement single file
    # create a temporary directory
    with tempfile.TemporaryDirectory() as directory:
        # if org == "tensorflow":
        #     return ["tensorflow"]
        imports = []

        Repo.clone_from("git://"+"github.com/"+org+"/"+repo, directory, depth=1, no_checkout=False, single_branch=True)

        if len(repoPath) > 0 and repoPath[0] != "/":
            repoPath = "/"+repoPath
        fileName = None
        pathParts = repoPath.split("/")
        if pathParts[-1].find(".") > 0:
            fileName = pathParts[-1]
            repoPath = "/".join(pathParts[:-1])
        # print("pathParts", pathParts)
        # print("repoPath", repoPath)
        # print("fileName", fileName)
        all_code_lines = []
        for path, subdirs, files in os.walk(directory+repoPath):
            innerPath = path[len(directory):]
            if innerPath.startswith("/."):
                continue
            if "init_net.pb" in files and "predict_net.pb" in files:
                if "caffe2" not in imports:
                    imports.append("caffe2")
            for name in files:
                if fileName is not None and name != fileName:
                    continue
                # print(path, innerPath, name)
                if fnmatch.fnmatch(name, "*.py"):
                    try:
                        with open(os.path.join(path, name), mode="r") as f:
                            lines = f.read()
                            all_code_lines += lines
                            result = extract_modules(lines)
                            for imp in result:
                                if imp not in imports:
                                    imports.append(imp)
                    except Exception as e:
                        print("Unable to read python file", os.path.join(path, name))
                if fnmatch.fnmatch(name, "*.ipynb"):
                    try:
                        with open(os.path.join(path, name), mode="r") as f:
                            code = json.load(f)
                            if 'cells' in code:
                                lines = []
                                for cell in code['cells']:
                                    if cell['cell_type'] == 'code':
                                        for line in cell['source']:
                                            lines.append(line)
                                all_code_lines += lines
                                result = extract_modules(" ".join(lines))
                                for imp in result:
                                    if imp not in imports:
                                        imports.append(imp)
                    except Exception as e:
                        print("Unable to parse ipynb file", os.path.join(path, name))
        #print("".join(all_code_lines[:10]))
        return sorted(imports)
