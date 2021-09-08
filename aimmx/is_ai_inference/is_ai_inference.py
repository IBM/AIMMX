from joblib import load
import numpy as np

from . import models

import warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    import importlib.resources as pkg_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources as pkg_resources

with pkg_resources.path(models, 'isai.joblib') as f:
    is_ai_pipeline = load(f)

def is_ai_inference(readme):
    result = is_ai_pipeline.predict([readme])
    return result[0]
