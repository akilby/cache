from setuptools import setup

setup(name='cache',
      version='0.1',
      description='Complex memoization to file',
      url='http://github.com/akilby/cache',
      author='Angela E. Kilby',
      author_email='a.kilby@northeastern.edu',
      license='MIT',
      packages=['cache'],
      install_requires=['pandas', 'numpy'],
      zip_safe=False,
      entry_points={
        'console_scripts': [
            'cluster = cache.config:config',
        ],
      }
      )
