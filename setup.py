#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
    readme = f.read()


requires = [
    'atom',
    'enaml',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
]

classifiers = [
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'License :: OSI Approved :: BSD License',
]

setup(
    name='ABR',
    version='0.0.2',
    author='Brad Buran',
    author_email='bburan@alum.mit.edu',
    description='ABR wave analyzer',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/bburan/abr',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
    classifiers=classifiers,
    entry_points={
        'console_scripts': [
            'abr = abr.app:main_launcher',
            'abr_gui = abr.app:main_gui',
            'abr_batch = abr.app:main_batch',
            'abr_compare = abr.app:main_compare',
        ]
    },
)
