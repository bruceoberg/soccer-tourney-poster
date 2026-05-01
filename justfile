# justfile

set positional-arguments

strProjectName  := "stp"
dirProjectRoot  := justfile_directory()
dirLoc          := dirProjectRoot / "src" / strProjectName / "localization"

pot-push:
    python {{dirProjectRoot}}/scripts/potpo.py push

po-accept +lPathInputs:
    python {{dirProjectRoot}}/scripts/potpo.py accept "$@"