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
        'caldav>=1.4.0',
        'tzlocal',
        'Click',
        'PyYAML',
        'requests',  ## Required for Ollama integration
        'sortedcontainers'
    ],
    
    extras_require={
    'voice': ['SpeechRecognition', 'pyaudio'],  ## Optional voice recognition support
},

    entry_points={
        'console_scripts': [
            'plann = plann.cli:cli',
            'plann-ai = plann.ai_cli:cli',
            'plann-ai-gui = plann.gui:main',
        ],
    },
   **metadata_
)
