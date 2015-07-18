from setuptools import setup, find_packages
import sys, os

version = '0.2'

setup(name='WebPF',
      version=version,
      description="Web Interface for Running PocketFEATURE",
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
          'pyFEATURE',
          'PocketFEATURE',
          'FEATUREdb',
          'flask',
      ],
      entry_points={}
)
