from distutils.core import setup
from pathlib import Path

short_description = "A simple python wrapper script for bootstrapping a reverse proxy inside a docker container."

try:
    if (Path().parent / "README.rst").is_file():
        with open(str(Path().parent / "README.rst")) as readme_file:
            long_description = readme_file.read()
    elif (Path().parent / "README.md").is_file():
        import m2r

        long_description = m2r.parse_from_file(Path().parent / "README.md")
    else:
        raise AssertionError("No readme file")
except (ImportError, AssertionError):
    long_description = short_description


setup(
    name="proxybootstrap",
    packages=["proxybootstrap"],
    version="0.1.8",
    license="MIT",
    description=short_description,
    long_description=long_description,
    author="romnn",
    author_email="contact@romnn.com",
    url="https://github.com/romnn/proxybootstrap",
    keywords=["reverse", "proxy", "container", "docker", "wrapper", "CORS", "nginx"],
    python_requires=">=3.6",
    install_requires=["jinja2"],
    extras_require=dict(dev=["m2r"]),
    package_data={"proxybootstrap": ["nginx.default.jinja2", "Dockerfile.jinja2"]},
    classifiers=[
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    entry_points={"console_scripts": ["proxybootstrap=proxybootstrap:main"]},
)
