# justfile

set positional-arguments

strProjectName  := "stp"
dirProjectRoot  := justfile_directory()
dirLoc          := dirProjectRoot / "src" / strProjectName / "localization"
strTournLatest  := "2026-mens-world-cup"
dirGridSrc      := dirProjectRoot / "playground" / "grid" / strTournLatest

dirObergOrg     := dirProjectRoot / ".." / "oberg-org"
dirZolaContent  := dirObergOrg / "zola" / "content"
dirPostsStp     := dirZolaContent / "posts" / "stp"

dirGridDst    := dirPostsStp / strTournLatest / "grid"

pot-push:
    python {{dirProjectRoot}}/scripts/potpo.py push

po-accept +lPathInputs:
    python {{dirProjectRoot}}/scripts/potpo.py accept "$@"

publish:
    rm -fr {{dirProjectRoot}}/published/{{strTournLatest}}/
    rm -fr {{dirProjectRoot}}/playground/published/{{strTournLatest}}/
    stp -d published -t {{strTournLatest}}
    mv {{dirProjectRoot}}/playground/published/{{strTournLatest}}/ {{dirProjectRoot}}/published/

copy-manifest:
    cp {{dirGridSrc}}/manifest.yaml {{dirGridDst}}

copy-grid:
    rm -fr {{dirGridDst}}
    cp -R {{dirGridSrc}} {{dirGridDst}}