#!/usr/bin/env python3
import os
import re
import shutil
import sys
from datetime import datetime

# ===============================
# FaceFix Utility
# Product: FaceFix
# Version: 7
# Author: Sanddino
# ===============================

PRODUCT_NAME = "FaceFix"
VERSION = "7"
AUTHOR = "Sanddino"

# ANSI color codes for highlighting
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"


def smart_replace(file_path, make_backup=True):
    """Replace lines like 'ps-tX = Resource<Name>...' with 'this = Resource<Name>...'.
       Optionally creates a .bak backup (e.g., MyFile_backup.bak) before changing.
       Highlights changes in the console output.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        replaced = 0
        changed_lines = []

        # Match ps-tX lines with all target resources
        pattern = re.compile(
            r'^\s*ps-t\d+\s*=\s*(Resource\w*(?:FaceDiffuse|FaceHeadDiffuse|FaceHeadNormalMap|FaceNormalMap)(?:[.\w]*)?)\s*$',
            re.IGNORECASE
        )

        for idx, line in enumerate(lines, 1):
            match = pattern.match(line.rstrip('\n'))
            if match:
                rhs = match.group(1)
                indent = re.match(r'^(\s*)', line).group(1)
                new_line = f"{indent}this = {rhs}\n"
                new_lines.append(new_line)
                replaced += 1
                changed_lines.append((idx, line.rstrip('\n'), new_line.rstrip('\n')))
            else:
                new_lines.append(line)

        if replaced > 0:
            # Create .bak backup unless disabled
            if make_backup:
                base, _ = os.path.splitext(file_path)
                backup_path = f"{base}_backup.bak"
                shutil.copyfile(file_path, backup_path)
                print(f"💾 Backup saved as '{os.path.relpath(backup_path)}'")
            else:
                print("⚠️ Backup creation skipped due to -nobackup flag.")

            # Overwrite file with updated content
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            print(f"✅ Changed '{os.path.relpath(file_path)}' — {replaced} line(s) replaced.")

            # Highlight changes in console
            for line_num, old, new in changed_lines:
                highlighted_old = re.sub(r'ps-t\d+', lambda m: f"{RED}{m.group(0)}{RESET}", old)
                highlighted_new = new.replace("this", f"{GREEN}this{RESET}")
                print(f"   Line {line_num}: '{highlighted_old}' → '{highlighted_new}'")
        else:
            print(f"ℹ️ No matching lines in '{os.path.relpath(file_path)}'.")

        return replaced > 0

    except Exception as e:
        print(f"❌ Error processing '{file_path}': {e}")
        return False


def main():
    # Display version info
    print(f"{PRODUCT_NAME} v{VERSION} — by {AUTHOR}\n")

    # Check for -nobackup argument
    make_backup = True
    if "-nobackup" in [arg.lower() for arg in sys.argv[1:]]:
        make_backup = False

    # Determine the folder the script is running from
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📂 Running in folder: {root_dir}\n")

    ini_files = []

    # Recursively walk through folders
    for dirpath, _, filenames in os.walk(root_dir):
        for f in filenames:
            if f.lower().endswith(".ini") and "disabled" not in f.lower():
                ini_files.append(os.path.join(dirpath, f))

    if not ini_files:
        print("⚠️ No eligible .ini files found in this folder or subfolders.")
        wait_for_exit()
        return

    print(f"🔍 Found {len(ini_files)} eligible .ini file(s). Processing...\n")

    files_processed = 0

    for ini_file in ini_files:
        changed = smart_replace(ini_file, make_backup=make_backup)
        if changed:
            files_processed += 1

    print(f"\n📁 Files processed: {len(ini_files)}")
    print(f"✅ Files modified: {files_processed}")
    print("\n🎉 Finished!")

    wait_for_exit()


def wait_for_exit():
    """Keep window open after finishing (useful when compiled as .exe)."""
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
