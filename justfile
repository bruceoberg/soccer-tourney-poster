# justfile

set positional-arguments

strProjectName  := "stp"
dirProjectRoot  := justfile_directory()
dirLoc          := dirProjectRoot / "src" / strProjectName / "localization"
tournLatest     := "2026-mens-world-cup"

pot-push:
    python {{dirProjectRoot}}/scripts/potpo.py push

po-accept +lPathInputs:
    python {{dirProjectRoot}}/scripts/potpo.py accept "$@"

publish:
    rm -fr {{dirProjectRoot}}/published/{{tournLatest}}/
    rm -fr {{dirProjectRoot}}/playground/published/{{tournLatest}}/
    stp -d published -t {{tournLatest}}
    mv {{dirProjectRoot}}/playground/published/{{tournLatest}}/ {{dirProjectRoot}}/published/
