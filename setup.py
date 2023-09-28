from __future__ import print_function
from setuptools import setup, find_packages

import os
import sys
import codecs


v = sys.version_info


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


shell = False
if os.name in ('nt', 'dos'):
    shell = True
    warning = "WARNING: Windows is not officially supported"
    print(warning, file=sys.stderr)


def main():
    setup(
        # Application name:
        name="kamunu",

        python_requires='>3.6',

        # Version number (initial):
        version=get_version('kamunu/_version.py'),

        # Application author details:
        author="Colav",
        author_email="colav@udea.edu.co",

        # Packages
        packages=find_packages(exclude=['tests']),

        # Include additional files into the package
        include_package_data=True,

        # Details
        url="https://github.com/colav-playground/kamunu/",
        scripts=['bin/kamunu_run'],
        #
        license="BSD",

        description="A package for searching organization identifiers in multiple search engines.",

        long_description=open("README.md").read(),

        long_description_content_type="text/markdown",

        # Dependent packages (distributions)
        install_requires=[
            'pymongo',
            'requests',
            'beautifulsoup4',
            'langdetect',
            'fuzzywuzzy',
            'python-Levenshtein',
            'unidecode',
            'deep-translator',
            'translators',
            'nltk',
            'html5lib',
            'pycountry',
            'nltk',
        ],
    )


if __name__ == "__main__":
    main()
