# Python and Jupyter in LazyVim

This configuration uses the official Python, DAP and Neotest extras, Pyright,
Ruff, blink.cmp, venv-selector, Jupytext, Molten and image.nvim.

## One-time setup

Install Neovim, uv and ImageMagick separately, then prepare the Python tools:

```sh
uv python install 3.13
uv tool install jupytext
uv venv --python 3.13 "${XDG_DATA_HOME:-$HOME/.local/share}/nvim/python-provider"
uv pip install --python "${XDG_DATA_HOME:-$HOME/.local/share}/nvim/python-provider/bin/python" \
  pynvim jupyter-client nbformat pillow cairosvg debugpy
```

In Neovim, run `:Lazy install`, `:MasonInstall pyright ruff`, and
`:UpdateRemotePlugins`, then restart. Check `:checkhealth jupytext molten`.
The Python extra also installs the required Treesitter parsers.

The Neovim Python provider is independent of project interpreters. The nearest
project `.venv` or `venv` is used for Python analysis and execution. Select an
alternative with `<leader>cv`; `<leader>cpi` displays the actual interpreter.
The selected project environment needs `ipykernel` for notebooks and `pytest`
for tests. Existing environments are reused; this configuration does not sync
project dependencies or modify lockfiles.

## Python

- `<leader>cpr`: run the current Python file.
- `<leader>cf`: format; `.py` files also format automatically on save.
- `<leader>ca`: code actions, including Ruff fixes.
- `K`: hover documentation; `gK`: signature help.
- `<leader>db`: breakpoint; `<leader>dc`: run/continue.
- `<leader>di` / `<leader>dO` / `<leader>do`: step into/over/out.
- `<leader>du`: debugger UI with variables and stack.
- `<leader>tr` / `<leader>tt` / `<leader>tT`: nearest test/file/suite.

## Notebooks

Open an `.ipynb` normally. Jupytext presents Python percent cells (`# %%`)
and Markdown comments (`# %% [markdown]`). Its temporary representation stays
in Neovim's cache, never beside project code.

| Keys | Action |
| --- | --- |
| `<leader>ji` | Select/init kernel; project interpreter is offered first |
| `<leader>jc` / `<leader>ja` | Run current cell / all code cells |
| `<leader>ju` / `<leader>jb` | Run cells above / current and below |
| `<leader>jn` / `<leader>jp` | Next / previous cell |
| `<leader>jo` / `<leader>jh` | Show / hide floating output |
| `<leader>jV` | Toggle inline output |
| `<leader>jr` / `<leader>js` | Restart / interrupt kernel |
| `<leader>jN` / `<leader>jM` | Add code / Markdown cell below |
| `<leader>jd` | Delete cell |
| `<leader>jK` / `<leader>jJ` | Move cell up / down |
| `<leader>jI` | Import saved outputs |
| `<leader>jw` | Save notebook and newly executed cell outputs |
| `<leader>jv` / `<leader>jB` | Open plot in image viewer / HTML in browser |
| `<leader>jl` / visual `<leader>je` | Run scratch line / selection |

`<leader>` is Space in the default LazyVim configuration. All mappings have
WhichKey descriptions. To scroll a floating output, run
`:noautocmd MoltenEnterOutput`; use `Ctrl-w p` to return to the code.

`:w` saves notebook text while retaining existing outputs. After execution
finishes, use `<leader>jw` to save new results. Output restoration happens
when a kernel is initialized; restoring outputs does not restore variables.
Save new results before changing cell structure or switching kernels.

## Limits

- Markdown remains editable text, rather than browser-rendered prose.
- IPython `%`/`!` syntax is preserved for execution, but regular Python LSP
  diagnostics may flag magic lines. Notebook-wide autoformat is disabled.
- Inline images use Kitty graphics in Ghostty/Kitty and ImageMagick CLI.
  Other terminals can use the external image viewer.
- Molten output import/export is experimental. Exports are merged only for
  executed whole cells; untouched outputs and metadata remain intact. Busy
  kernels and duplicate code cells block safe export. Use JupyterLab when
  the notebook cannot be matched safely.
- Scratch line/selection execution is not intended for notebook output export.
- Molten may export stdout/stderr as textual display data instead of preserving
  separate stream names. Existing notebook outputs retain their original form.
- LaTeX rendering, Plotly, widgets and external Jupyter servers require
  additional optional dependencies and are not configured here.
