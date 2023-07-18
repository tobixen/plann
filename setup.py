#!/usr/bin/env python

import sys
import os

from setuptools import setup, find_packages

from plann.metadata import metadata
metadata_ = metadata.copy()

for x in metadata:
    if not x in ('author', 'version', 'license', 'maintainer', 'author_email',
                 'status', 'name', 'description', 'url', 'description'):
        metadata_.pop(x)

setup(
    packages=['plann'],
    classifiers=[
        #"Development Status :: ..."
        "Environment :: Web Environment",
        #"Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content :: CGI Tools/Libraries",
    ],
    py_modules=['plann'],
    install_requires=[
        'icalendar',
        'caldav>=0.12-dev0',
#        'isodate',
        'tzlocal',
        'Click',
        'PyYAML',
        'sortedcontainers'
    ],

    entry_points={
        'console_scripts': [
            'plann = plann.cli:cli',
        ],
    },
   **metadata_
)
