<p align="center">
    <img src="https://raw.githubusercontent.com/datatorch/documentation/master/docs/.vuepress/public/python.png" width="180" />
</p>

<h1 align="center">
  DataTorch Python
</h1>
<h4 align="center">DataTorch CLI and Python API libary for programmatic access.</h4>

<p align="center">
  <img alt="Package Version" src="https://img.shields.io/pypi/v/datatorch">
  <img alt="Python Versions" src="https://img.shields.io/pypi/pyversions/datatorch">
  <img alt="Build Status" src="https://img.shields.io/github/actions/workflow/status/datatorch/python/package.yml?branch=master">
</p>

## Installation

*Note*: Newer versions (>=0.4.8.2) of DataTorch client require `libmagic` for file uploads
to datasets. Your system may or may not have `libmagic` pre-installed. Please
make sure you have `libmagic` installed before proceeding.

```bash
pip install datatorch
```

## Development

```bash
python3 -m pip install --editable .
pip3 install -r requirements.txt
```

### VSCode Configuration

#### Formatter

Open your VSCode settings, by going `Code -> Preferences -> Settings`. Search
for "python formatting provider" and select "black" from the dropdown menu.
