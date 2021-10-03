import io
import os

from setuptools import find_packages, setup

# Package meta-data.
NAME = "reconchess-tools"
DESCRIPTION = "Tools for developing bots to play reconchess."
URL = "https://github.com/raaperrotta/reconchess-tools"
EMAIL = "raaperrotta@gmail.com"
AUTHOR = "Robert Perrotta"
REQUIRES_PYTHON = ">=3.6.0"
VERSION = "0.2.1"

# What packages are required for this module to be executed?
REQUIRED = [
    "reconchess",
    "tqdm",
    "click",
]

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# If you change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

# Load the package's __version__.py module as a dictionary.
about = {"__version__": VERSION}

# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=["tests"]),
    entry_points={
        "console_scripts": ["reconchess-tools=reconchess_tools.cli.main:cli"],
    },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license="MIT",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
