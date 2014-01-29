from setuptools import setup, find_packages
import sys, os

version = '0.1'

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
          'numpy>=1.6.2',
          'sh>=1.09',
      ],
      entry_points={}
)
