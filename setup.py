from setuptools import setup
import sys

py_version = sys.version_info[:2]

if py_version < (2, 7):
    raise RuntimeError('On Python 2, meld3 requires Python 2.7 or later')
elif (3, 0) < py_version < (3, 4):
    raise RuntimeError('On Python 3, meld3 requires Python 3.4 or later')

install_requires = []

CLASSIFIERS = [
    'Development Status :: 7 - Inactive',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Topic :: Text Processing :: Markup :: HTML'
    ]

UNMAINTAINED = """
    No further development of the meld3 package is planned.  The meld3 package
    should be considered unmaintained as of April 2020.  Since 2007, meld3
    received only minimal updates to keep compatible with newer Python versions.
    It was only maintained because it was a dependency of the Supervisor package.
    Since Supervisor 4.1.0 (released in October 2019), the meld3 package is
    no longer a dependency of Supervisor.
"""

setup(
    name = 'meld3',
    version = '2.0.1',
    description = 'Unmaintained templating system used by old versions of Supervisor',
    long_description = UNMAINTAINED,
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
