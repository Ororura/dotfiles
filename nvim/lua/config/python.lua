local M = { choices = {} }

function M.root(path)
  path = path or vim.api.nvim_buf_get_name(0)
  if path == "" then
    path = vim.uv.cwd()
  end
  return vim.fs.root(path, { "pyproject.toml", "pyrightconfig.json", "setup.py", ".git" }) or vim.fs.dirname(path)
end

function M.python(root)
  root = root or M.root()
  if M.choices[root] and vim.fn.executable(M.choices[root]) == 1 then
    return M.choices[root]
  end
  local dir = root
  while dir do
    for _, name in ipairs({ ".venv", "venv" }) do
      local python = dir .. "/" .. name .. "/bin/python"
      if vim.fn.executable(python) == 1 then
        return python
      end
    end
    dir = vim.fs.dirname(dir)
  end
  if vim.env.VIRTUAL_ENV and vim.fn.executable(vim.env.VIRTUAL_ENV .. "/bin/python") == 1 then
    return vim.env.VIRTUAL_ENV .. "/bin/python"
  end
  return vim.fn.exepath("python3")
end

function M.selected()
  local python = require("venv-selector").python()
  if not python then
    return
  end
  M.choices[M.root()] = python
  for _, client in ipairs(vim.lsp.get_clients({ name = "pyright", bufnr = 0 })) do
    client.settings.python.pythonPath = python
    client:notify("workspace/didChangeConfiguration", { settings = client.settings })
  end
end

function M.run()
  if vim.fn.expand("%:e") == "ipynb" then
    return vim.notify("Use <leader>jc / <leader>ja for notebooks", vim.log.levels.WARN)
  end
  vim.cmd.update()
  Snacks.terminal({ M.python(), vim.api.nvim_buf_get_name(0) }, { cwd = M.root(), start_insert = true })
end

return M
