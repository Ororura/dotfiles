return {
  {
    "GCBallesteros/jupytext.nvim",
    lazy = false,
    opts = { style = "percent", output_extension = "auto" },
    config = function(_, opts)
      -- The upstream plugin normally creates a sibling .py. Keep its temporary
      -- representation in the cache instead, so it cannot overwrite project code.
      local dir = vim.fn.stdpath("cache") .. "/jupytext-" .. vim.fn.getpid()
      vim.fn.mkdir(dir, "p")
      require("jupytext.utils").get_jupytext_file = function(path, extension)
        return dir .. "/" .. vim.fn.sha256(vim.fn.fnamemodify(path, ":p")) .. "." .. extension
      end
      local commands = require("jupytext.commands")
      local run = commands.run_jupytext_command
      commands.run_jupytext_command = function(input, args)
        args["--opt"] = table.concat(
          vim.tbl_map(vim.fn.shellescape, {
            "notebook_metadata_filter=all",
            "cell_metadata_filter=all",
            "comment_magics=false",
          }),
          " --opt="
        )
        return run(input, args)
      end
      -- Upstream's healthcheck still uses the removed report_* API.
      package.loaded["jupytext.health"] = {
        check = function()
          vim.health.start("jupytext.nvim")
          local cli = vim.fn.exepath("jupytext")
          if cli == "" then
            return vim.health.error("Jupytext CLI is missing from PATH")
          end
          local result = vim.system({ cli, "--version" }, { text = true }):wait()
          if result.code == 0 then
            vim.health.ok("Jupytext " .. vim.trim(result.stdout) .. " — " .. cli)
          else
            vim.health.error(result.stderr or "Jupytext CLI failed")
          end
        end,
      }
      require("jupytext").setup(opts)
      require("config.notebook").setup()
      vim.api.nvim_create_autocmd("VimLeavePre", {
        callback = function()
          vim.fn.delete(dir, "rf")
        end,
      })
    end,
  },
  {
    "benlubas/molten-nvim",
    lazy = false,
    build = ":UpdateRemotePlugins",
    init = function()
      local graphics = vim.env.KITTY_WINDOW_ID or vim.env.TERM_PROGRAM == "ghostty" or vim.env.TERM == "xterm-ghostty"
      vim.g.molten_image_provider = graphics and "image.nvim" or "none"
      vim.g.molten_auto_open_output = false
      vim.g.molten_virt_text_output = true
      vim.g.molten_wrap_output = true
      vim.g.molten_output_win_max_height = 20
    end,
    keys = {
      {
        "<leader>ji",
        function()
          require("config.notebook").init()
        end,
        desc = "Initialize / Select Kernel",
      },
      {
        "<leader>jc",
        function()
          require("config.notebook").run("current")
        end,
        desc = "Run Cell",
      },
      {
        "<leader>ja",
        function()
          require("config.notebook").run("all")
        end,
        desc = "Run All Cells",
      },
      {
        "<leader>ju",
        function()
          require("config.notebook").run("above")
        end,
        desc = "Run Cells Above",
      },
      {
        "<leader>jb",
        function()
          require("config.notebook").run("below")
        end,
        desc = "Run Cell and Below",
      },
      {
        "<leader>jn",
        function()
          require("config.notebook").jump(1)
        end,
        desc = "Next Cell",
      },
      {
        "<leader>jp",
        function()
          require("config.notebook").jump(-1)
        end,
        desc = "Previous Cell",
      },
      { "<leader>jo", "<cmd>MoltenShowOutput<cr>", desc = "Show Output" },
      { "<leader>jh", "<cmd>MoltenHideOutput<cr>", desc = "Hide Output Window" },
      { "<leader>jV", "<cmd>MoltenToggleVirtual<cr>", desc = "Toggle Inline Output" },
      { "<leader>jr", "<cmd>MoltenRestart<cr>", desc = "Restart Kernel" },
      { "<leader>js", "<cmd>MoltenInterrupt<cr>", desc = "Interrupt Kernel" },
      {
        "<leader>jN",
        function()
          require("config.notebook").add(false)
        end,
        desc = "Add Code Cell Below",
      },
      {
        "<leader>jM",
        function()
          require("config.notebook").add(true)
        end,
        desc = "Add Markdown Cell Below",
      },
      {
        "<leader>jd",
        function()
          require("config.notebook").delete()
        end,
        desc = "Delete Cell",
      },
      {
        "<leader>jK",
        function()
          require("config.notebook").move(-1)
        end,
        desc = "Move Cell Up",
      },
      {
        "<leader>jJ",
        function()
          require("config.notebook").move(1)
        end,
        desc = "Move Cell Down",
      },
      {
        "<leader>jI",
        function()
          require("config.notebook").import()
        end,
        desc = "Restore Saved Outputs",
      },
      {
        "<leader>jw",
        function()
          require("config.notebook").export()
        end,
        desc = "Save Notebook and New Outputs",
      },
      { "<leader>jv", "<cmd>MoltenImagePopup<cr>", desc = "Open Plot in Image Viewer" },
      { "<leader>jB", "<cmd>MoltenOpenInBrowser<cr>", desc = "Open HTML Output in Browser" },
      { "<leader>jl", "<cmd>MoltenEvaluateLine<cr>", desc = "Run Line (Scratch Output)" },
      { "<leader>je", ":<C-u>MoltenEvaluateVisual<cr>gv", mode = "x", desc = "Run Selection (Scratch Output)" },
    },
  },
  {
    "3rd/image.nvim",
    lazy = true,
    build = false,
    opts = {
      backend = "kitty",
      processor = "magick_cli",
      max_height_window_percentage = 40,
      integrations = { markdown = { enabled = false }, neorg = { enabled = false } },
    },
  },
  { "folke/which-key.nvim", opts = { spec = { { "<leader>j", group = "Jupyter" } } } },
}
