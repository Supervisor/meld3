from distutils.core import setup, Extension
import os
import sys

if sys.version_info[:2] < (2, 3):
    msg = ("meld3 requires Python 2.3 or later. You are using version %s. "
           "Please install using a supported version." % sys.version)
    sys.stderr.write(msg)
    sys.exit(1)

if os.environ.get('USE_MELD3_EXTENSION_MODULES'):
    ext_modules=[Extension("meld3/cmeld3",
                           ["meld3/cmeld3.c"])]
else:
    # by default, allow people to install meld3 without building the
    # extension modules (meld works fine without them, it's just slower).
    ext_modules = []

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2 :: Only',
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
    license='ZPL 2.1',
    packages=['meld3'],
    url='https://github.com/supervisor/meld3',
    ext_modules=ext_modules,
)
