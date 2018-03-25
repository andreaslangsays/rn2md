from distutils.core import setup

setup(
    name='RedNotebookToMarkDown',
    version='0.2dev',
    description='Utility to print RedNotebook data in the MarkDown format.',
    long_description=open('README.txt').read(),
    url='http://github.com/brianrodri/RednotebookToMarkdown',
    author='Brian Rodriguez',
    author_email='brian@brianrodri.com',
    license='MIT',
    packages=['rn2md'],
    install_requires=[
        'dateutil',
        'defaultlist',
        'freezegun',
        'isoweek',
        'parsedatetime',
        'pyfakefs',
        'yaml',
    ],
)
