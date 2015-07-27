from setuptools import setup, find_packages
import sys, os

version = '0.4'
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
          'argparse',
          'numpy',
          'scipy',
          'biopython',
          'munkres',
          'six',
      ],
      entry_points={
        'console_scripts': [
            pf_task_script('extract:PocketExtraction', 'pf-extract'),
            pf_task_script('compare:FeatureFileComparison', 'pf-compare'),
            pf_task_script('align:ScoreAlignment', 'pf-align'),
            pf_task_script('rmsd:AlignmentRmsdComputation', 'pf-rmsd'),
            pf_task_script('visualize:VisAlign', 'pf_vis'),
            pf_task_script('full_comparison:ComparePockets', 'run_pf'),
            pf_task_script('build_background:GeneratePocketFeatureBackground', 'pf_genbg'),
            pf_task_script('benchmark:BenchmarkPocketFeatureBackground', 'pf_bench'),
        ]
      }
)
