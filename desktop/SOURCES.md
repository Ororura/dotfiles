# Assets and upstream components

- Catppuccin Mocha palettes/themes: https://github.com/catppuccin/waybar,
  https://github.com/catppuccin/yazi, https://github.com/catppuccin/btop.
- JetBrains Mono patched Nerd Font: https://github.com/ryanoasis/nerd-fonts.
  Selected installed font files are included with the original SIL OFL in
  `fonts/JetBrainsMonoNerdFont/OFL.txt`.
- Personal wallpaper `niri/wallpapers/current.jpg`: existing user image
  `village-street-neon-girl-umbrella-y6-3840x2160.jpg`, downloaded from
  https://hdqwalls.com/wallpaper/3840x2160/village-street-neon-girl-umbrella.
- `mocha-waves.svg`/PNG: custom abstract wallpaper from this desktop setup.
- Yazi: https://github.com/sxyazi/yazi/releases/tag/v26.9.1.
  Archive SHA256 agrees with the official release asset digest.
- OpenRGB: https://openrgb.org/releases.html, official 1.1 Linux x86_64 AppImage.
  SHA256 was computed from the downloaded official release asset; it is not
  a publisher signature. Downloads and extracted binaries are pinned in
  `assets.lock.json` and are not stored in Git.
- RGB protocol and SDK fields follow OpenRGB release_1.1 sources:
  https://gitlab.com/CalcProgrammer1/OpenRGB/-/tree/release_1.1/Controllers/GigabyteRGBFusionGPUController
  and `NetworkProtocol.h` / `RGBController/RGBController.cpp`.
