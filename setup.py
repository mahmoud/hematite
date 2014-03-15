# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = list(f)

setup(name='hematite',
      version='0.0.1',
      author='Mahmoud Hashemi and Mark Williams',
      url='https://github.com/mahmoud/hematite',
      install_requires=requirements,
      packages=find_packages(),
      license='BSD',
      classifiers=[
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers']

      )
