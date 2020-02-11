"""
    Given a GitHub repo, attempts to automatically identify frameworks used
"""

from github3.exceptions import NotFoundError
import base64, re
from ..util.gh_utils import get_file_from_repo

FRAMEWORKS = ["tensorflow", "scikit-learn", "scikit_learn", "sklearn", "keras", "theanos", "torch", "caffe", "caffe2", "nltk", "theano", "lasagne", "mxnet"]

# Expects repo object from github.repo
def repo_framework(repo_object):

    frameworks = {}
    requirements = get_file_from_repo(repo_object, "requirements.txt")
    if requirements is None:
        requirements = get_file_from_repo(repo_object, "requirement.txt")
    if requirements is not None:
        modules = requirements.split("\n")
        for m in modules:
            s = re.split('==|>=|~=|>',m.lower())
            if s[0].strip() in FRAMEWORKS:
                fw = s[0].strip()
                frameworks[fw] = ""
                if len(s) > 1:
                    frameworks[fw] = s[1].strip()

    return frameworks
