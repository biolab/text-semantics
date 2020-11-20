import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="text-semantics",  # Replace with your own username
    version="0.0.1",
    author="Bioinformatics Laboratory, FRI UL and Revelo d. o. o.",
    author_email="contact@orange.biolab.si",
    description="The package with scripts for semantic analyser project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/biolab/text-semantics",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "requests",
        "pyyaml",
        "beautifulsoup4",
        "pandas",
        "docx2txt",
        "pdfminer3k",
        "odfpy",
    ],
)
