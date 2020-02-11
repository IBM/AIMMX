from setuptools import setup

VERSION="0.0.1"
setup(
    name='aimmx',
    version=VERSION,
    description='Automated aI Model Metadata eXtractor',
    url='https://github.ibm.com/aimodels/AIMMX',
    author='Jason Tsay',
    author_email='jason.tsay@ibm.com',
    license='IBM',
    packages=['aimmx'],
    install_requires=[
        'requests',
        'bs4',
        'github3.py',
        'arxiv',
        'python-dateutil',
        'pyyaml',
        'bibtexparser',
        'joblib',
        'scikit-learn',
        'gitpython',
        'markdown',
        'importlib_resources'
    ],
    zip_safe=False
)
