from setuptools import setup, Extension
import os
import sys

py_version = sys.version_info[:2]
PY3 = py_version[0] == 3

if PY3:
    if py_version < (3, 2):
        raise RuntimeError('On Python 3, meld3 requires Python 3.2 or later')
else:
    if py_version < (2, 3):
        raise RuntimeError('On Python 2, meld3 requires Python 2.3 or later')

install_requires = []
if sys.version_info[:2] < (2, 5):
    install_requires.append('elementtree')

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.3",
    "Programming Language :: Python :: 2.4",
    "Programming Language :: Python :: 2.5",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.2",
    "Programming Language :: Python :: 3.3",
    'Topic :: Text Processing :: Markup :: HTML'
    ]

setup(
    name = 'meld3',
    version = '0.6.10',
    description = 'meld3 is an HTML/XML templating engine.',
    classifiers = CLASSIFIERS,
    author = 'Chris McDonough',
    author_email = 'chrism@plope.com',
    maintainer = "Mike Naberezny",
    maintainer_email = "mike@naberezny.com",
    license = 'BSD-derived (http://www.repoze.org/LICENSE.txt)',
    install_requires = install_requires,
    packages = ['meld3'],
    test_suite = 'meld3',
    url = 'https://github.com/supervisor/meld3'
)
