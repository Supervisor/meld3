from distutils.core import setup, Extension
import os

if os.environ.get('USE_MELD3_EXTENSION_MODULES'):
    ext_modules=[Extension("meld3/cmeld3",
                           ["meld3/cmeld3.c"])]
else:
    # by default, allow people to install meld3 without building the
    # extension modules (meld works fine without them, it's just
    # slower).
    ext_modules = []

setup(
    name = 'meld3',
    version = '0.6.6',
    description = 'meld3 is an HTML/XML templating engine.',
    author = 'Chris McDonough',
    author_email =  'chrism@plope.com',
    license='see LICENSE.txt',
    packages=['meld3'],
    url='http://dist.repoze.org/meld3/',
    ext_modules=ext_modules,
)
