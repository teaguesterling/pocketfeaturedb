from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(name='pyFEATURE',
      version=version,
      description="Wrappers for running FATURE in Python",
      long_description="""\
Python interface to the Stanford FEATURE biomolecular structure analysis tools""",
      author='Teague Sterling',
      author_email='teague@mail.sfsu.edu',
      url='http://feature.stanford.edu',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'numpy',
          'sh',
          'six',
      ],
      entry_points={}
)
