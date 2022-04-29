from setuptools import setup, Distribution

# !! git tags as a single source of truth regarding version numbers

# Make sure versiontag exists before going any further. This won't actually install
# the package. It will just download the egg file into `.eggs` so that it can be used
# henceforth in setup.py.
Distribution().fetch_build_eggs('versiontag')

# Import versiontag components
from versiontag import get_version, cache_git_tag

# This caches for version in version.txt so that it is still accessible if
# the .git folder disappears, for example, after the slug is built on Heroku.
cache_git_tag()

setup(
    name='commandr',
    version=get_version(pypi=True),
    packages=['commandr'],
    url='',
    license='MIT',
    author='Myrousz',
    author_email='',
    description='Commandr',
    python_requires='>=3.8',
    install_requires = [
        'versiontag>=1.1.1',
        'pyyaml'
    ],
    package_data={'': ['requirements.txt', 'README.md']},
    include_package_data=True
)
