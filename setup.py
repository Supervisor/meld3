from setuptools import setup
import sys

py_version = sys.version_info[:2]

if py_version < (2, 5):
        raise RuntimeError('On Python 2, meld3 requires Python 2.5 or later')
elif (3, 0) < py_version < (3, 2):
        raise RuntimeError('On Python 3, meld3 requires Python 3.2 or later')

install_requires = []

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.5',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Topic :: Text Processing :: Markup :: HTML'
    ]

setup(
    name = 'meld3',
    version = '1.0.0dev',
    description = 'meld3 is an HTML/XML templating engine.',
    classifiers = CLASSIFIERS,
    author = 'Chris McDonough',
    author_email = 'chrism@plope.com',
    maintainer = "Chris McDonough",
    maintainer_email = "chrism@plope.com",
    license = 'BSD-derived (http://www.repoze.org/LICENSE.txt)',
    install_requires = install_requires,
    packages = ['meld3'],
    test_suite = 'meld3',
    url = 'https://github.com/supervisor/meld3'
)
