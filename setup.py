from setuptools import setup

with open("README.md", "r") as fp:
    long_description = fp.read()

requirements = [

]


setup(
    name='datatorch',
    version='0.0.1',
    description='A CLI and library for interacting with DataTorch',
    author='DataTorch',
    author_email='justin@datatorch.io',
    entry_points={
        'console_scripts': [
            'datatorch=datatorch.cli:main',
            'dt=datatorch.cli:main'
        ]
    },
    url='https://github.com/datatorch/python',
    long_description=long_description,
    install_requirements=requirements,
    license='MIT license',
    zip_safe=False
)
