# Using pybricksdev with Jupyter notebooks

Here are some tips on using `pybricksdev` with Jupyter notebooks.

- Create a virtual environment for hosting the kernel.
- Required packages: `pybricksdev`, `notebook`, `ipykernel`, `ipywidgets`
- Enable widgets for progress bars: `jupyter nbextension enable --py widgetsnbextension`
- Create a named kernel: `python -m ipykernel install --user --name=pybricksdev`
- Start a notebook server: `jupyter notebook`
