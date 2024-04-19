import os

from setuptools import setup


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]


setup(
    name='zc_events',
    version='0.4.1',
    description="Shared code for ZeroCater microservices events",
    long_description='',
    keywords='zerocater python util',
    author='ZeroCater',
    author_email='tech@zerocater.com',
    url='https://github.com/ZeroCater/zc_events',
    download_url='https://github.com/ZeroCater/zc_events/tarball/0.4.1',
    license='MIT',
    packages=get_packages('zc_events'),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
    ],
    install_requires=[
        'boto3>=1.4.7',
        'celery>=3.1.10',
        'inflection>=0.3.1,<0.4',
        # These changes mirror the workaround we used to fix py-gateway builds
        # https://github.com/ZeroCater/zc_events/compare/ctowstik/mp-962-pika-zc-events
        # https://zerocater-eng.atlassian.net/browse/MP-962
        # pika <= 0.11 cannot be used with Python 3.7+ due to `async` keyword being reserved
        'pika>=0.11.0,<=1.3.2',
        'pika-pool @ git+https://github.com/ZeroCater/pika-pool@059e9e5cd3bd42d0cd7e376abd0d668f0faafc14#egg=pika-pool',  # noqa
        'redis>=2.10.5,<=3.5.3',

        'ujson>=1.35,<1.36',
        'zc_common>=0.4.18',
        'pyjwt>=1.4.0,<2.0.0',
        'six>=1.10.0'
    ]
)
