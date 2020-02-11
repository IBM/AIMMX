import sys
from .clone import get_py_modules
from .framework_util import getFrameworks
from git.exc import GitCommandError
import traceback

def extract_framework(repo_url):

    url_parts = repo_url.split("/")
    for i in range(0, len(url_parts)):
        url_parts[i] = url_parts[i].lower()

    #print(url_parts)
    org = url_parts[3]
    reponame = url_parts[4]
    repopath = "/".join(url_parts[7:len(url_parts)])
    if not repopath:
        repopath = ""

    response_json = {'success': False}

    response_json['success'] = True
    #response_json["modules"] = get_py_modules(org, reponame)
    modules = get_py_modules(org, reponame)
    response_json["frameworks"] = getFrameworks(modules)
    #print(response_json)
    return response_json
