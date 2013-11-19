from setuptools import setup, find_packages
import os

version = '0.0.0'

requires = [
    'setuptools',
    'requests',
    'pyramid',
    'Paste',
    'WebError',
    'repoze.tm2',
    'pyramid_exclog',
    'psycopg2',
]

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'docs', 'HISTORY.txt')).read()

setup(name='monassis-server-sync',
      version=version,
      description="The Monassis synchronisation server",
      long_description=README + "\n\n" + CHANGES,
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        ],
      keywords='',
      author='Carl Scheffler',
      author_email='carl@siyavula.com',
      url='https://github.com/Siyavula/monassis-server-sync',
      license='Copyright (C) Siyavula Education (Pty) Ltd',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['monassis'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      test_requires=requires,
      entry_points = """\
      [paste.app_factory]
      main = monassis.syncserver:main
      """,
      paster_plugins=['pyramid'],
      )
