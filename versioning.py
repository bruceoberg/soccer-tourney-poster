#!/usr/bin/env python3

# 'annotations' allow typing hints to forward reference.
#	e.g. Fn(fwd: CFwd) instead of Fn(fwd: 'CFwd')
#	when CFwd is later in file.
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

class CRepositoryVersion:  # tag = repover
    """Repository Version info"""
    
    def __init__(self):
        """Get current git state."""
        self.strHashGit = ""
        self.strHashGitShort = ""
        self.fDirty = False
        self.tGenerated = datetime.now()
        
        try:
            pathRepo = Path(__file__).parent
            
            # Get full hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=pathRepo,
                capture_output=True,
                text=True,
                check=True
            )
            self.strHashGit = result.stdout.strip()
            
            # Get short hash
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=pathRepo,
                capture_output=True,
                text=True,
                check=True
            )
            self.strHashGitShort = result.stdout.strip()
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=pathRepo,
                capture_output=True,
                text=True,
                check=True
            )
            self.fDirty = bool(result.stdout.strip())
            
        except FileNotFoundError:
            # Git command not found in PATH
            pass
        except subprocess.CalledProcessError:
            # Git command failed (not a repo, etc.)
            pass
    
    def __bool__(self) -> bool:
        """True if git version info was successfully retrieved."""
        return bool(self.strHashGit)
    
    def StrVersionShort(self) -> str:
        """Format version string for document footer/header."""
        if not self:
            return "unknown"
        
        strDirty = "-dirty" if self.fDirty else ""
        return f"v{self.strHashGitShort}{strDirty}"
    
    def ObjFullInfo(self) -> dict:
        """Full version info for document metadata."""
        return {
            "version": self.StrVersionShort(),
            "git_commit": self.strHashGit if self else "",
            "generated_at": self.tGenerated.isoformat(),
            "has_uncommitted_changes": self.fDirty
        }
    
g_repover = CRepositoryVersion()
