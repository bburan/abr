#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    readme = f.read()

packages = [
    'abr',
]

package_data = {
    'abr': ['data/*'],
}

requires = [
    'wxpython',
    'numpy',
    'matplotlib',
    'scipy',
    'pandas',
]

classifiers = [
        'Operating System :: OS Independent',
        'Programming Language :: Python',
]

setup(
    name='ABR',
    description='ABR wave analyzer',
    long_description=readme,
    packages=packages,
    package_data=package_data,
    install_requires=requires,
    classifiers=classifiers,
    entry_points={
        'console_scripts': [
            'abr_gui = abr.app.cmd_main:main',
            'abr_loop = abr.app.cmd_main_loop:main',
        ]
    },
)
