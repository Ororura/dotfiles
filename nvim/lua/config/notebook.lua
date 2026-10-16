local M = { dirty = {} }
local function notify(message)
  vim.notify(message, vim.log.levels.WARN, { title = "Jupyter" })
end
local function trim(s)
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end
local function source(cell)
  local value = cell.source
  return type(value) == "table" and table.concat(value) or value
end

-- Parse percent cells, leaving the Jupytext metadata header outside cells.
function M.cells()
  local lines, cells = vim.api.nvim_buf_get_lines(0, 0, -1, false), {}
  for i, line in ipairs(lines) do
    if line:match("^# %%%%") then
      if #cells > 0 then
        cells[#cells].last = i - 1
      end
      cells[#cells + 1] = {
        marker = i,
        first = i + 1,
        markdown = line:find("[markdown]", 1, true) ~= nil or line:find("[raw]", 1, true) ~= nil,
      }
    end
  end
  if #cells == 0 and vim.bo.filetype == "python" and not vim.api.nvim_buf_get_name(0):match("%.ipynb$") then
    cells = { { marker = 1, first = 1 } }
  end
  if #cells > 0 then
    cells[#cells].last = #lines
  end
  local row, current = vim.api.nvim_win_get_cursor(0)[1], 1
  for i, cell in ipairs(cells) do
    cell.stop = cell.last
    while cell.stop >= cell.first and lines[cell.stop]:match("^%s*$") do
      cell.stop = cell.stop - 1
    end
    cell.text = table.concat(vim.list_slice(lines, cell.first, cell.stop), "\n")
    if row >= cell.marker then
      current = i
    end
  end
  return cells, current
end

local function ready()
  if #vim.fn.MoltenRunningKernels(true) == 0 then
    notify("Initialize a kernel with <leader>ji first")
    return false
  end
  return true
end

function M.init()
  if not vim.tbl_isempty(M.dirty[vim.api.nvim_get_current_buf()] or {}) then
    return notify("Save new outputs with <leader>jw before switching kernels")
  end
  local python = require("config.python").python()
  local check = vim.system({ python, "-c", "import ipykernel" }, { text = true }):wait()
  local preferred
  if check.code == 0 then
    preferred = "nvim-" .. vim.fn.sha256(python):sub(1, 12)
    local dir = vim.fn.stdpath("data") .. "/jupyter/kernels/" .. preferred
    vim.fn.mkdir(dir, "p")
    vim.fn.writefile({
      vim.json.encode({
        argv = { python, "-m", "ipykernel_launcher", "-f", "{connection_file}" },
        display_name = "Project: " .. python,
        language = "python",
      }),
    }, dir .. "/kernel.json")
  end
  local kernels = vim.fn.MoltenAvailableKernels()
  if preferred then
    for i = #kernels, 1, -1 do
      if kernels[i] == preferred then
        table.remove(kernels, i)
      end
    end
    table.insert(kernels, 1, preferred)
  end
  vim.ui.select(kernels, {
    prompt = "Jupyter kernel (project first)",
    format_item = function(k)
      return k == preferred and ("Project — " .. python) or k
    end,
  }, function(kernel)
    if kernel then
      if #vim.fn.MoltenRunningKernels(true) > 0 then
        vim.cmd.MoltenDeinit()
      end
      vim.cmd.MoltenInit(kernel)
    end
  end)
end

function M.import()
  if vim.fn.expand("%:e") == "ipynb" and ready() then
    vim.cmd.MoltenImportOutput(vim.api.nvim_buf_get_name(0))
  end
end

function M.run(which)
  if not ready() then
    return
  end
  local cells, current = M.cells()
  local buf = vim.api.nvim_get_current_buf()
  M.dirty[buf] = M.dirty[buf] or {}
  for i, cell in ipairs(cells) do
    local selected = which == "all"
      or (which == "current" and i == current)
      or (which == "above" and i < current)
      or (which == "below" and i >= current)
    if selected and not cell.markdown and cell.stop >= cell.first then
      vim.fn.MoltenEvaluateRange(cell.first, cell.stop)
      M.dirty[buf][trim(cell.text)] = true
    end
  end
end

function M.jump(direction)
  local cells, index = M.cells()
  local cell = cells[index + direction]
  if cell then
    vim.api.nvim_win_set_cursor(0, { cell.marker, 0 })
    vim.cmd("normal! zv")
  end
end

local function clear_outputs()
  if not vim.tbl_isempty(M.dirty[vim.api.nvim_get_current_buf()] or {}) then
    notify("Save new outputs with <leader>jw before changing cell structure")
    return false
  end
  if #vim.fn.MoltenRunningKernels(true) > 0 then
    vim.cmd("MoltenDelete!")
  end
  return true
end

function M.add(markdown)
  local cells, index = M.cells()
  if not clear_outputs() then
    return
  end
  local at = cells[index] and cells[index].last or vim.api.nvim_buf_line_count(0)
  vim.api.nvim_buf_set_lines(
    0,
    at,
    at,
    false,
    { "", markdown and "# %% [markdown]" or "# %%", markdown and "# " or "", "" }
  )
  vim.api.nvim_win_set_cursor(0, { at + 3, markdown and 2 or 0 })
end

function M.delete()
  local cells, index = M.cells()
  local cell = cells[index]
  if not cell then
    return
  end
  if not clear_outputs() then
    return
  end
  vim.api.nvim_buf_set_lines(0, cell.marker - 1, cell.last, false, {})
end

function M.move(direction)
  local cells, index = M.cells()
  local cell, other = cells[index], cells[index + direction]
  if not cell or not other then
    return
  end
  if not clear_outputs() then
    return
  end
  local a, b = cells[math.min(index, index + direction)], cells[math.max(index, index + direction)]
  local first = vim.api.nvim_buf_get_lines(0, a.marker - 1, a.last, false)
  local second = vim.api.nvim_buf_get_lines(0, b.marker - 1, b.last, false)
  -- A final cell need not end in a blank line; keep a separator when moving it.
  if second[#second] ~= "" then
    second[#second + 1] = ""
  end
  local replacement = vim.list_extend(vim.deepcopy(second), first)
  vim.api.nvim_buf_set_lines(0, a.marker - 1, b.last, false, replacement)
  vim.api.nvim_win_set_cursor(0, { direction < 0 and a.marker or a.marker + #second, 0 })
end

-- Molten's exporter is experimental and can reduce MIME bundles of imported
-- outputs. Export to a temporary copy, then merge ONLY cells run by our cell
-- commands. Untouched outputs and metadata stay byte-for-byte equivalent as JSON.
function M.export()
  if vim.fn.expand("%:e") ~= "ipynb" then
    return notify("This command saves .ipynb buffers only")
  end
  if not ready() then
    return
  end
  local path, buf = vim.fn.resolve(vim.api.nvim_buf_get_name(0)), vim.api.nvim_get_current_buf()
  local dirty = M.dirty[buf] or {}
  if vim.tbl_isempty(dirty) then
    vim.cmd.write()
    return
  end
  local cells = M.cells()
  local counts = {}
  for _, cell in ipairs(cells) do
    if not cell.markdown then
      local normalized = require("remove_comments").remove_comments(cell.text .. "\n", "python")
      counts[normalized] = (counts[normalized] or 0) + 1
      if counts[normalized] > 1 then
        return notify("Duplicate code cells: use JupyterLab to export outputs safely")
      end
    end
  end
  local state_path = vim.fn.tempname() .. ".json"
  vim.cmd.MoltenSave(state_path)
  local state = vim.json.decode(table.concat(vim.fn.readfile(state_path), "\n"))
  vim.fn.delete(state_path)
  for _, cell in ipairs(state.cells) do
    if cell.status == 0 or cell.status == 1 then
      return notify("Kernel is busy; wait before exporting outputs")
    end
  end
  vim.cmd.write()
  local original = vim.json.decode(table.concat(vim.fn.readfile(path), "\n"))
  local tmp = vim.fs.dirname(path) .. "/." .. vim.fs.basename(path) .. ".nvim-" .. vim.fn.getpid() .. ".ipynb"
  local candidate = vim.deepcopy(original)
  for _, cell in ipairs(candidate.cells) do
    if cell.cell_type == "code" and dirty[trim(source(cell))] then
      cell.outputs, cell.execution_count = {}, vim.NIL
    end
  end
  vim.fn.writefile({ vim.json.encode(candidate) }, tmp)
  local ok, err = pcall(function()
    vim.cmd.MoltenExportOutput({ args = { tmp }, bang = true })
    local exported = vim.json.decode(table.concat(vim.fn.readfile(tmp), "\n"))
    local merged = 0
    for i, cell in ipairs(original.cells) do
      if cell.cell_type == "code" and dirty[trim(source(cell))] then
        local result = exported.cells[i]
        if result.execution_count == vim.NIL or result.execution_count == nil then
          error("Cell has no completed execution; wait for output, then save again")
        end
        cell.outputs, cell.execution_count = result.outputs, result.execution_count
        merged = merged + 1
      end
    end
    if merged == 0 then
      error("Code changed since execution; rerun the edited cells")
    end
    vim.fn.writefile({ vim.json.encode(original) }, tmp)
    local stat = vim.uv.fs_stat(path)
    if stat then
      assert(vim.uv.fs_chmod(tmp, stat.mode))
    end
    assert(vim.uv.fs_rename(tmp, path))
    M.dirty[buf] = nil
    vim.notify("Saved outputs for " .. merged .. " executed cells", vim.log.levels.INFO)
  end)
  vim.fn.delete(tmp)
  if not ok then
    notify(tostring(err))
  end
end

function M.setup()
  local data = vim.fn.stdpath("data") .. "/jupyter"
  vim.env.JUPYTER_PATH = data .. (vim.env.JUPYTER_PATH and (":" .. vim.env.JUPYTER_PATH) or "")
  local group = vim.api.nvim_create_augroup("user_python_notebooks", { clear = true })
  vim.api.nvim_create_autocmd("FileType", {
    group = group,
    pattern = "python",
    callback = function(ev)
      vim.bo[ev.buf].expandtab, vim.bo[ev.buf].shiftwidth, vim.bo[ev.buf].tabstop = true, 4, 4
      if vim.api.nvim_buf_get_name(ev.buf):match("%.ipynb$") then
        -- Whole-file Ruff formatting can change cell boundaries/magics and
        -- invalidate saved outputs. Python scripts retain LazyVim autoformat.
        vim.b[ev.buf].autoformat = false
      end
    end,
  })
  vim.api.nvim_create_autocmd("User", {
    group = group,
    pattern = "MoltenInitPost",
    callback = function()
      local buf = vim.api.nvim_get_current_buf()
      vim.schedule(function()
        if vim.api.nvim_buf_is_valid(buf) then
          vim.api.nvim_buf_call(buf, M.import)
        end
      end)
    end,
  })
  vim.api.nvim_create_autocmd("BufWipeout", {
    group = group,
    callback = function(ev)
      M.dirty[ev.buf] = nil
    end,
  })
end
return M
