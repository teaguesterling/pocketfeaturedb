from setuptools import setup, find_packages
import sys, os

version = '0.1'
PF_TASKS = 'pocketfeature.tasks'

def pf_task_script(task, script):
   return "{0} = {1}.{2}.run_as_script".format(script, PF_TASKS, task)

setup(name='PocketFEATURE',
      version=version,
      description="PocketFEATURE algorithms and FEATURE wrappers",
      author='Teague Sterling, Tianyun Lui',
      author_email='teague@mail.sfsu.edu',
      url='http://feature.stanford.edu',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
#          'numpy>=1.8.0',
          'biopython>=1.60',
          'munkres>=1.0.6',
          'FEATUREwrappers>=0.1dev',
      ],
      entry_points={
        'console_scripts': [
            pf_task_script('pocket:PocketFinder', 'pf_extract'),
        ]
      }
)
