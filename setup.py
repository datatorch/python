from setuptools import setup, find_packages
import sys

# Ensure the Python version is 3.12 or higher
assert sys.version_info >= (3, 12, 0), "DataTorch requires Python 3.12+"

with open("README.md", "r", encoding="utf-8") as fp:
    long_description = fp.read()

requirements = [
    "Click==8.0.0",
    "gql==3.4.0",
    "websockets==10.4",
    "websocket-client",
    "requests==2.31.0",
    "typing_extensions>=4.1.0",
    "psutil~=5.9.4",
    "aiodocker~=0.19.0",
    "Jinja2~=2.0",
    "PyYAML~=6.0",
    "aiostream~=0.4.0",
    "markupsafe==2.0.1",
    "requests_toolbelt==0.10.1",
    "imantics==0.1.12",
    "shapely==2.0.6",  # Compatible Python 3.13
    "tqdm~=4.65.0",
    "urllib3==1.26.15",
    "numpy",
    "docker",
    "python-magic",
    "pycocotools",
]

setup(
    name="datatorch",
    version="0.4.8.5",
    description="A CLI and library for interacting with DataTorch.",
    author="DataTorch",
    author_email="support@datatorch.io",
    entry_points={
        "console_scripts": ["datatorch=datatorch.cli:main", "dt=datatorch.cli:main"]
    },
    url="https://github.com/datatorch/python",
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    python_requires=">=3.12",
    license="MIT license",
    zip_safe=False,
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
