from setuptools import setup, find_packages

version = '0.1'

setup(name='TaskBase',
      version=version,
      description="Task Base Utilities",
      author='Teague Sterling',
      author_email='teaguesterling@gmail.com',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'argparse',
      ],
)
