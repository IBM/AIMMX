# AIMMX
AI Model Metadata eXtractor

Python library that infers and extracts AI model-specific metadata from GitHub repositories.

## Requirements

Runs on Python3 with the dependencies as described in `requirements.txt`

Also will require a GitHub API key which can be obtained by the following steps:

* On [GitHub](https://github.com/), click your profile picture in the top-right

* [Settings > Developer Settings > Personal access tokens > "Generate new token"](https://github.com/settings/tokens)

* Keep track of the key that is generated for use later (see Usage)

## Installation

In the root directory of the library, please run `pip3 install -e .`

## Usage

```Python
from aimmx import AIMMX

if __name__ == '__main__':
    aimmx = AIMMX("***INSERT GITHUB API KEY HERE***)
    metadata = aimmx.repo_parse("***INSERT GITHUB URL TO ANALYZE HERE***")
    print(metadata)
```

## Examples

Please see the `examples` folder for a Jupyter notebook with various examples.
