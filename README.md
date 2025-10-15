hole
====

A program to analyze the pore dimensions of ion channels. 

Please see the homepage http://www.holeprogram.org/ for further information.

Supported platforms
-------------------

* Linux
* macOS (Intel and Apple silicon)

Installation
------------

* **Source code** is available at https://github.com/osmart/hole2/ . Compiling requires a working FORTRAN compiler. See [INSTALL.md](INSTALL.md) for installation instructions.

* For **Linux**, the [hole2 conda-forge package](https://anaconda.org/conda-forge/hole2) is available and can be installed with
  ```bash
  conda install -c conda-forge hole2
  ```
* For **macOS** (Intel and Apple silicon) an _experimental_ conda-forge [hole2 package](https://anaconda.org/conda-forge/hole2) exists for Intel builds. Apple silicon users can now build the project from source directly (see below) or download CI artifacts produced by this repository.

* For **Windows** you need to compile `hole2` yourself but this has never been officially supported. If you succeed in building hole2 in Windows then please share successful recipes in issue [#16](https://github.com/osmart/hole2/issues/16).


Testing
-------

After compiling the suite (for example with `make -C src`) you can validate the build by running the regression tests that replay the documented examples:

```
python3 -m pytest
```
