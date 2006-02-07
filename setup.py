from distutils.core import setup, Extension

setup(
    name = 'meld3',
    version = '0.4',
    description = 'meld3 is an HTML/XML templating engine.',
    author = 'Chris McDonough',
    author_email =  'chrism@plope.com',
    license='see LICENSE.txt',
    packages=['meld3'],
    url='http://www.plope.com/software/meld3',
    ext_modules=[Extension("meld3/cmeld3",
                           ["meld3/cmeld3.c"])]
)
