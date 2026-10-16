-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Keep Neovim's remote Python host independent of project environments.
vim.g.python3_host_prog = vim.fn.stdpath("data") .. "/python-provider/bin/python"
vim.g.lazyvim_python_lsp = "pyright"
vim.g.lazyvim_python_ruff = "ruff"
local tool_bin = vim.fn.expand("~/.local/bin")
if not vim.tbl_contains(vim.split(vim.env.PATH or "", ":"), tool_bin) then
  vim.env.PATH = tool_bin .. ":" .. (vim.env.PATH or "")
end
