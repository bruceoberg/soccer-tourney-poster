{ pkgs, lib, config, inputs, ... }:

{
  packages = with pkgs;
  [
    gettext # manipulate .pot/.po files
    just    # run stuff in the justfile
    icu     # for language aware string sorting
  ];

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
