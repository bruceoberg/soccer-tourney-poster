{ pkgs, lib, config, inputs, ... }:

{
  languages.python =
  {
    enable = true;
    version = "3.13";
    venv.enable = true;

    uv =
    {
      enable = true;
      sync.enable = true;  # Auto-sync dependencies on direnv reload
    };
  };

  # Tell uv to use devenv's venv
  
  env.UV_PROJECT_ENVIRONMENT = "${config.devenv.root}/.devenv/state/venv";

  # See full reference at https://devenv.sh/reference/options/
}
