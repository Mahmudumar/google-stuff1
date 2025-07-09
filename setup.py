from setuptools import setup

setup(
    name='BobsiMo Activities',
    version='1.0.0',
    py_modules=['GUI', "core"],
    entry_points={
        'console_scripts': [
            'bma = GUI:main',
        ],
    },
)