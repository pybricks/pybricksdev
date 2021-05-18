# Using pybricksdev with Jupyter notebooks

Here are some tips on using `pybricksdev` with Jupyter notebooks.

- Create a virtual environment for hosting the kernel (remember `pybricksdev` is Python 3.8 only!).
- Use `apt`, `brew`, `pipx`, etc. and not `pip` for installing notebook server globally.
- Required packages for kernel: `pybricksdev`, `ipykernel`, `ipywidgets`
- Recommended packages for kernel: `matplotlib`
- Create a named kernel: `python -m ipykernel install --user --name=pybricksdev`
- Required packages for notebook server (classic): `notebook`, `widgetsnbextension`
- Required packages for notebook server (new): `jupyterlab`, `jupyterlab_widgets`
- Enable widgets for progress bars (should only be needed for older versions):
  `jupyter nbextension enable --py widgetsnbextension`
- Start a notebook server (classic): `jupyter notebook`
- Start a notebook server (new): `jupyter lab`
- Can use VS Code `ms-toolsai.jupyter` extension instead of installing and running your own server.
