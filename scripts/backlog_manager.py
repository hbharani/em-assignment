#!/usr/bin/env python3
"""
LangGraph Agent for GitHub Backlog Management
Reads architecture docs and creates issues via Gemini + gh CLI

Entry point - delegates to modularized backlog package
"""

import json
import subprocess
from pathlib import Path

from backlog import run_backlog_manager, delete_all_issues


def main():
    """Main entry point for backlog manager"""
    import sys

    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    cleanup = "--cleanup" in sys.argv
    cleanup_only = "--cleanup-only" in sys.argv

    if cleanup_only:
        # Only cleanup, don't run workflow
        print("=" * 70)
        print("?? CLEANUP MODE")
        print("=" * 70)
        delete_all_issues()
    elif cleanup:
        # Delete all issues then run workflow
        print("=" * 70)
        print("?? DELETE AND RECREATE MODE")
        print("=" * 70)
        repo_root = Path(__file__).parent.parent
        
        print("\n?? Starting deletion phase...")
        deleted_count = delete_all_issues(skip_confirmation=True)
        print(f"\n? Deletion phase complete: {deleted_count} issues deleted")
        
        # Verify deletion worked
        print(f"\n?? Verifying deletion success...")
        import time
        time.sleep(1)  # Brief pause for GitHub to process
        
        verify_result = subprocess.run(
            "gh issue list --state all --json number,title --limit 100",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_root,
        )
        
        try:
            remaining_issues = json.loads(verify_result.stdout) if verify_result.returncode == 0 else []
            if remaining_issues:
                print(f"??  {len(remaining_issues)} issues still exist after deletion:")
                for issue in remaining_issues[:10]:
                    print(f"   - #{issue.get('number')}: {issue.get('title', 'N/A')}")
                print(f"\n??  Some issues may not have been deleted. Proceeding to create new ones...")
            else:
                print(f"? All issues deleted successfully (0 remaining)")
        except Exception as e:
            print(f"??  Could not verify deletion: {str(e)}")
        
        print(f"\n?? Now creating new issues from architecture docs...")
        run_backlog_manager(dry_run=dry_run)
    else:
        # Normal run
        run_backlog_manager(dry_run=dry_run)


if __name__ == "__main__":
    main()
