from setuptools import setup, find_packages

setup(
    name="iptv_scrapers",
    version="1.3.2",
    packages=find_packages(),
    install_requires=[
        'requests',
        'beautifulsoup4'
    ]
)