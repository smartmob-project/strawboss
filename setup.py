# -*- coding: utf-8 -*-

from setuptools import find_packages, setup

with open('README.rst', 'rb') as stream:
    readme = stream.read()
    if hasattr(readme, 'decode'):
        readme = readme.decode('utf-8')

with open('strawboss/version.txt', 'r') as stream:
    version = stream.read()
    if hasattr(version, 'decode'):
        version = version.decode('utf-8')
    version = version.strip()

setup(
    name='strawboss',
    url='https://github.com/smartmob-project/strawboss',
    description='',
    long_description=readme,
    keywords='',
    maintainer='Andre Caron',
    maintainer_email='ac@smartmob.org',
    version=version,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries',
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'strawboss = strawboss:main',
         ],
    },
)
