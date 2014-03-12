from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = list(f)

if __name__ == '__main__':
    setup(name='ransom',
          version='0.0',
          install_requires=requirements,
          packages=find_packages())
