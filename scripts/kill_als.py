#!/usr/bin/env python3
"""Kill Ada Language Server processes and clean up stale locks.

This script performs aggressive cleanup of ALS processes and lock files,
similar to adafmt's preflight behavior. Useful for cleaning up stuck 
processes and locks during development or before running tests.

Usage:
    python kill_als.py              # Kill all ALS processes & clean locks
    python kill_als.py --safe       # Kill only stale ALS processes (>30 min)
    python kill_als.py --dry-run    # Show what would be done without doing it
    python kill_als.py --locks-only # Only clean lock files, don't kill processes
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path to import adafmt modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from adafmt.utils import kill_als_processes, find_stale_locks, list_als_pids


def main():
    parser = argparse.ArgumentParser(
        description="Kill Ada Language Server processes and clean up stale locks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--safe", 
        action="store_true",
        help="Safe mode: only kill processes older than 30 minutes (default: kill all)"
    )
    
    parser.add_argument(
        "--stale-minutes",
        type=int,
        default=30,
        help="In safe mode, consider processes older than this stale (default: 30)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information"
    )
    
    parser.add_argument(
        "--locks-only",
        action="store_true",
        help="Only clean lock files, don't kill processes"
    )
    
    parser.add_argument(
        "--no-locks",
        action="store_true",
        help="Don't clean lock files, only kill processes"
    )
    
    args = parser.parse_args()
    
    # Build cleanup summary
    actions_taken = []
    
    # Handle processes
    if not args.locks_only:
        # List current ALS processes
        pids = list_als_pids()
        
        if pids:
            print(f"Found {len(pids)} ada_language_server process(es): {pids}")
        else:
            print("No ada_language_server processes found.")
        
        if pids and not args.dry_run:
            # Kill processes
            killed = kill_als_processes(
                mode="aggressive" if not args.safe else "safe",
                stale_minutes=args.stale_minutes,
                dry_run=args.dry_run
            )
            actions_taken.append(f"Killed {killed} process(es)")
        elif pids and args.dry_run:
            print(f"Would kill {len(pids)} process(es) in {'safe' if args.safe else 'aggressive'} mode")
    
    # Handle lock files
    if not args.no_locks:
        # Find ALS directories to search for locks
        from pathlib import Path
        search_paths = []
        
        # ~/.als directory
        als_home = Path.home() / ".als"
        if als_home.exists():
            search_paths.append(als_home)
        
        # XDG_DATA_HOME location
        import os
        xdg_data = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
        als_xdg = Path(xdg_data) / 'als'
        if als_xdg.exists():
            search_paths.append(als_xdg)
        
        stale = find_stale_locks(
            search_paths=search_paths,
            ttl_minutes=args.stale_minutes if args.safe else 0
        )
        
        if stale:
            print(f"\nFound {len(stale)} stale lock director{'y' if len(stale) == 1 else 'ies'}:")
            for lock_dir in stale:
                print(f"  {lock_dir}")
                
            if not args.dry_run:
                # Remove stale locks
                import shutil
                removed = 0
                for lock_dir in stale:
                    try:
                        shutil.rmtree(lock_dir)
                        removed += 1
                        if args.verbose:
                            print(f"  Removed: {lock_dir}")
                    except Exception as e:
                        print(f"  Error removing {lock_dir}: {e}")
                
                actions_taken.append(f"Removed {removed} lock director{'y' if removed == 1 else 'ies'}")
            else:
                print(f"Would remove {len(stale)} lock director{'y' if len(stale) == 1 else 'ies'}")
        else:
            if not args.locks_only:
                print("\nNo stale lock directories found.")
    
    # Summary
    if args.dry_run:
        print("\nDry run completed - no changes made.")
    elif actions_taken:
        print(f"\nCleanup completed: {', '.join(actions_taken)}")
    else:
        print("\nNo cleanup needed.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())