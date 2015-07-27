import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

requires = [
    'pyramid',
    'python-dateutil',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'waitress',
    'newrelic',
    'psycopg2',
    'gunicorn',
    'nose',
    'webtest',
    'requests']

setup(name='syncserver',
      version='1.3',
      description='Synchronisation service for the network of Monassis instances',
      long_description=README,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pyramid",
          "Topic :: Internet :: WWW/HTTP",
          "Topic :: Internet :: WWW/HTTP :: WSGI :: Application"],
      author='Carl Scheffler',
      author_email='carl@siyavula.com',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='syncserver',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = syncserver:main
      [console_scripts]
      initialize_db = syncserver.scripts.initializedb:main
      """)
