from setuptools import setup, find_packages
import sys

assert sys.version_info >= (3, 6, 0), "DataTorch requires Python 3.6+"

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()

requirements = ["Click~=7.0", "numpy", "gql~=2.0.0"]

requirements_agents = ["psutil~=5.0"]

setup(
    name="datatorch",
    version="0.1.2",
    description="A CLI and library for interacting with DataTorch",
    author="DataTorch",
    author_email="support@datatorch.io",
    entry_points={
        "console_scripts": ["datatorch=datatorch.cli:main", "dt=datatorch.cli:main"]
    },
    url="https://github.com/datatorch/python",
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requirements=requirements,
    extra_require={"agents": requirements_agents},
    python_requires=">=3.6",
    license="MIT license",
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
