import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_chameleon',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'pingdomlib==1.5',
    'gevent',
    'gevent-websocket==0.3.6',
    'pyramid_beaker',
    'pyramid_sockjs',
    'fig',

    # For Postgres Connections
    'psycopg2',
]

setup(
    name='sams',
    version='0.0',
    description='sams',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Britt Gresham',
    author_email='brittcgresham@gmail.com',
    url='https://github.com/demophoon/sams',
    keywords='web wsgi bfg pylons pyramid pingdom monitor dashboard',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite='sams',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = sams:main
    [console_scripts]
    initialize_sams_db = sams.scripts.initializedb:main
    """,
)
