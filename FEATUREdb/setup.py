from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='FEATUREdb',
      version=version,
      description="SQL Interface and shell for FEATURE db",
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
          'flask',
          'flask-sqlalchemy',
          'sqlalchemy',
      ],
      entry_points={}
)
