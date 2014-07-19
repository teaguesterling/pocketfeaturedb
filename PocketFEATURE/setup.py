from setuptools import setup, find_packages
import sys, os

version = '0.2'
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
          'numpy>=1.6.2',
          'scipy>=0.7.0',
          'biopython>=1.58',
          'munkres>=1.0.6',
          'pyFEATURE>=0.1dev',
      ],
      entry_points={
        'console_scripts': [
            pf_task_script('pocket:PocketFinder', 'pf_extract'),
            pf_task_script('compare:FeatureFileCompare', 'pf_compare'),
            pf_task_script('align:AlignScores', 'pf_align'),
            pf_task_script('featurize:Featurize', 'pf_featurize'),
            pf_task_script('visualize:VisAlign', 'pf_vis'),
            pf_task_script('full_comparison:ComparePockets', 'run_pf'),
            pf_task_script('build_background:GeneratePocketFeatureBackground', 'pf_genbg'),
            pf_task_script('benchmark:BenchmarkPocketFeatureBackground', 'pf_bench'),
        ]
      }
)
