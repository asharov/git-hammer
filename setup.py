import setuptools

with open('README.md', 'r') as file:
    long_description = file.read()

setuptools.setup(
    name='git-hammer',
    version='0.3.2',
    author='Jaakko Kangasharju',
    author_email='ashar@iki.fi',
    description='Statistics tool for git repositories',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/asharov/git-hammer',
    packages=setuptools.find_packages(exclude=['tests']),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent'
    ],
    python_requires='>=3.7',
    install_requires=[
        'gitpython',
        'sqlalchemy >=1.4.7, <2.0',
        'sqlalchemy-utils >=0.37.0',
        'matplotlib <3.1',
        'python-dateutil',
        'globber',
        'beautifultable'
    ]
)
