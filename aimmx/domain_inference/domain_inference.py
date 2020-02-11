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

with pkg_resources.path(models, 'vision-domain-pipeline.joblib') as f:
    vision_domain_pipeline = load(f)

with pkg_resources.path(models, 'nlp-domain-pipeline.joblib') as f:
    nlp_domain_pipeline = load(f)

with pkg_resources.path(models, 'other-domain-pipeline.joblib') as f:
    other_domain_pipeline = load(f)

with pkg_resources.path(models, 'vision-task-pipeline.joblib') as f:
    vision_task_pipeline = load(f)

with pkg_resources.path(models, 'vision-le-preprocessing.joblib') as f:
    vision_le = load(f)

with pkg_resources.path(models, 'nlp-task-pipeline.joblib') as f:
    nlp_task_pipeline = load(f)

with pkg_resources.path(models, 'nlp-le-preprocessing.joblib') as f:
    nlp_le = load(f)

with pkg_resources.path(models, 'other-task-pipeline.joblib') as f:
    other_pipeline = load(f)

with pkg_resources.path(models, 'other-le-preprocessing.joblib') as f:
    other_le = load(f)

# vision_domain_pipeline = load('models/vision-domain-pipeline.joblib')
# nlp_domain_pipeline = load('models/nlp-domain-pipeline.joblib')
# other_domain_pipeline = load('models/other-domain-pipeline.joblib')
# vision_task_pipeline = load('models/vision-task-pipeline.joblib')
# vision_le = load('models/vision-le-preprocessing.joblib')
# nlp_task_pipeline = load('models/nlp-task-pipeline.joblib')
# nlp_le = load('models/nlp-le-preprocessing.joblib')
# other_pipeline = load('models/other-task-pipeline.joblib')
# other_le = load('models/other-le-preprocessing.joblib')


def domain_inference(readme):
    return_json = { "domain_type": "Unknown" }

    predicted_vision = vision_domain_pipeline.predict_proba([readme])
    predicted_nlp = nlp_domain_pipeline.predict_proba([readme])
    predicted_other = other_domain_pipeline.predict_proba([readme])

    categories = ["Computer Vision", "Natural Language Processing", "Other", "Unknown"]
    # print(predicted_vision, predicted_nlp, predicted_other)
    probs = np.array([ max(predicted_vision[0]), max(predicted_nlp[0]), max(predicted_other[0])])
    results = np.array([ np.argmax(predicted_vision[0]), np.argmax(predicted_nlp[0]), np.argmax(predicted_other[0])])
    # print(probs, results)

    # if only one is True
    cat_index = -1
    trues = np.sum(results)
    if trues == 0:
        cat_index = 3
    elif trues == 1:
        cat_index = np.where(results == 1)[0][0]
    elif trues >= 2:
        true_index = np.where(results == 1)[0]
        for i in range(len(results)):
            if i not in true_index:
                probs[i] = 0
        cat_index = np.argmax(probs)

    if cat_index != 3 and probs[cat_index] > 0.5:
        return_json["domain_type"] = categories[cat_index]
        return_json["domain_prob"] = probs[cat_index]
        # do the task or other
        if categories[cat_index] == "Computer Vision":
            predicted = vision_task_pipeline.predict_proba([readme])
            # print("predicted", predicted)
            prob = max(predicted[0])
            result_index = np.argmax(predicted[0])
            label = vision_le.inverse_transform([result_index])
            return_json["task"] = label[0]
            return_json["task_prob"] = prob
        elif categories[cat_index] == "Natural Language Processing":
            predicted = nlp_task_pipeline.predict_proba([readme])
            prob = max(predicted[0])
            result_index = np.argmax(predicted[0])
            label = nlp_le.inverse_transform([result_index])
            return_json["task"] = label[0]
            return_json["task_prob"] = prob
        else:
            predicted = other_pipeline.predict_proba([readme])
            prob = max(predicted[0])
            result_index = np.argmax(predicted[0])
            label = other_le.inverse_transform([result_index])
            return_json["domain_type"] = label[0]
            return_json["domain_prob"] = prob

    return return_json
