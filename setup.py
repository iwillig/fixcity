from setuptools import setup

version='0.1dev'

setup(name='fixcity',
      version=version,
      description="Build me a bike rack!",
      author="Ivan Willig, Paul Winkler, Sonali Sridhar, Andy Cochran, etc.",
      author_email="iwillig@opengeo.org",
      url="http://www.plope.com/software/ExternalEditor",
      zip_safe=False,
      #scripts=['zopeedit.py'],
      #packages=packages,
      dependency_links=[
        'http://geopy.googlecode.com/svn/branches/reverse-geocode#egg=geopy-0.93dev',
        ],
      install_requires=[
        'geopy==dev,>=0.93dev-r84',
        'sorl-thumbnail',
        'Django>=1.1',
        ],
      )
