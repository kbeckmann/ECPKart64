import os
import sys

from setuptools import setup, find_packages

setup(
    # Vitals
    name='ecpkart64',
    license='BSD',
    url='https://github.com/kbeckmann/ECPKart64',
    author='Konrad Beckmann',
    author_email='konrad.beckmann@gmail.com',
    description='ECPKart64 N64 development tool',

    # Imports / exports / requirements.
    platforms='any',
    packages=find_packages(include=["ecpkart64", "ecpkart64.*"]),
    include_package_data=True,
    python_requires="~=3.9",
    install_requires=['nmigen'],
    setup_requires=['setuptools'],
)
