from setuptools import setup, find_packages

setup(
    name='upchups-assistant',
    version='1.0.0',
    packages=find_packages(),
    # This is the magic part!
    entry_points={
        'console_scripts': [
            'upchups = upchups:main',
        ],
    },
)