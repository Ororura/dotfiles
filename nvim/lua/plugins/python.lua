return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        pylsp = { enabled = false },
        pyright = {
          before_init = function(_, config)
            config.settings.python.pythonPath = require("config.python").python(config.root_dir)
          end,
          settings = {
            pyright = { disableOrganizeImports = true, disableTaggedHints = false },
            python = {
              analysis = {
                typeCheckingMode = "basic",
                autoSearchPaths = true,
                diagnosticMode = "openFilesOnly",
              },
            },
          },
        },
      },
    },
  },
  {
    "mfussenegger/nvim-dap-python",
    config = function()
      local dp = require("dap-python")
      dp.setup(vim.g.python3_host_prog)
      dp.resolve_python = function()
        return require("config.python").python()
      end
      dp.test_runner = "pytest"
      for _, config in ipairs(require("dap").configurations.python or {}) do
        if config.request == "launch" then
          config.pythonPath = function()
            return require("config.python").python()
          end
        end
      end
    end,
  },
  {
    "nvim-neotest/neotest",
    opts = {
      adapters = {
        ["neotest-python"] = {
          runner = "pytest",
          python = function(root)
            return require("config.python").python(root)
          end,
        },
      },
    },
  },
  {
    "linux-cultist/venv-selector.nvim",
    opts = {
      options = {
        on_venv_activate_callback = function()
          require("config.python").selected()
        end,
      },
    },
  },
  {
    "folke/which-key.nvim",
    opts = { spec = { { "<leader>cp", group = "Python" } } },
  },
  {
    "folke/snacks.nvim",
    keys = {
      {
        "<leader>cpr",
        function()
          require("config.python").run()
        end,
        desc = "Run Python File",
        ft = "python",
      },
      {
        "<leader>cpi",
        function()
          vim.notify(require("config.python").python(), vim.log.levels.INFO, { title = "Python interpreter" })
        end,
        desc = "Show Python Interpreter",
        ft = "python",
      },
    },
  },
}
