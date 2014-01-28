from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='FEATUREwrappers',
      version=version,
      description="Wrappers for running FATURE in Python",
      long_description="""\
Wrappers to ensure easy environment consistency when running FEATURE from Python""",
      author='Teague Sterling',
      author_email='teague@mail.sfsu.edu',
      url='http://feature.stanford.edu',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'numpy>=1.8.0',
          'sh>=1.09',
      ],
      entry_points={}
)
