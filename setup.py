from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as fp:
    long_description = fp.read()

requirements = [
    'Click>=7.0.0'
]

setup(
    name='datatorch',
    version='0.0.1',
    description='A CLI and library for interacting with DataTorch',
    author='DataTorch',
    author_email='support@datatorch.io',
    entry_points={
        'console_scripts': [
            'datatorch=datatorch.cli:main',
            'dt=datatorch.cli:main'
        ]
    },
    url='https://github.com/datatorch/python',
    packages=['datatorch'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requirements=requirements,
    python_requires='>=3.6',
    license='MIT license',
    zip_safe=False
)
