# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="phone-mcp",
    use_scm_version=True,
    setup_requires=["setuptools-scm"],
    packages=find_packages(),
    install_requires=[
        "mcp>=1.6.0,<2",
        "aiohttp>=3.8.0",
        "asyncio>=3.4.3",
        "pypinyin>=0.54.0",
        "requests>=2.31.0",
    ],
    author="hao",
    author_email="hao@hao.com",
    description="A phone control plugin for MCP that allows you to control your Android phone through ADB commands to connect any human",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/hao-cyber/phone-mcp",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    entry_points={
        "mcp.plugins": ["phone=phone_mcp:mcp"],
        "console_scripts": [
            "phone-mcp=phone_mcp.__main__:main",
            "phone-cli=phone_mcp.cli:main",
        ],
    },
    keywords=["mcp", "phone", "android", "adb"],
    include_package_data=True,
)
