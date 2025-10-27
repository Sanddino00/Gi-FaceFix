#!/usr/bin/env python3
import os
import re
import shutil
import sys
import platform

# ===============================
# FaceFix Utility
# Product: FaceFix
# Version: 7.3
# Author: Sanddino
# ===============================

PRODUCT_NAME = "FaceFix"
VERSION = "7.3"
AUTHOR = "Sanddino"

# Check if color is supported
def supports_color():
    if sys.platform.startswith('win'):
        return os.getenv('ANSICON') is not None or 'WT_SESSION' in os.environ or platform.release() >= '10'
    if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        return True
    return False

COLOR_ENABLED = supports_color()
RED = "\033[91m" if COLOR_ENABLED else ""
GREEN = "\033[92m" if COLOR_ENABLED else ""
RESET = "\033[0m" if COLOR_ENABLED else ""

def smart_replace(file_path, make_backup=True, preview=True):
    """Scan and optionally replace lines in the file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        changed_lines = []

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
                changed_lines.append((idx, line.rstrip('\n'), new_line.rstrip('\n')))
            else:
                new_lines.append(line)

        if not changed_lines:
            return False, []

        if preview:
            print(f"\nPreview changes for '{os.path.relpath(file_path)}':")
            for idx, old, new in changed_lines:
                highlighted_old = re.sub(r'ps-t\d+', lambda m: f"{RED}{m.group(0)}{RESET}", old)
                highlighted_new = new.replace("this", f"{GREEN}this{RESET}")
                print(f"  Line {idx}: '{highlighted_old}' → '{highlighted_new}'")

        if make_backup:
            base, _ = os.path.splitext(file_path)
            backup_path = f"{base}_backup.bak"
            shutil.copyfile(file_path, backup_path)
            print(f"💾 Backup saved as '{os.path.relpath(backup_path)}'")

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        return True, changed_lines

    except Exception as e:
        print(f"❌ Error processing '{file_path}': {e}")
        return False, []

def main():
    print(f"{PRODUCT_NAME} v{VERSION} — by {AUTHOR}\n")

    make_backup = True
    if "-nobackup" in [arg.lower() for arg in sys.argv[1:]]:
        make_backup = False

    if getattr(sys, 'frozen', False):
        root_dir = os.path.dirname(sys.executable)
    else:
        root_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"📂 Running in folder: {root_dir}\n")

    # Ask user to specify folder to scan
    folder = input("Enter folder to scan for .ini files (or press ENTER for current folder): ").strip()
    if not folder:
        folder = root_dir
    folder = os.path.abspath(folder)

    # Ask if subfolders should be included
    scan_subfolders = input("Scan subfolders recursively? (y/n): ").strip().lower() == 'y'

    # Collect .ini files
    ini_files = []
    for dirpath, _, filenames in os.walk(folder):
        for f in filenames:
            if f.lower().endswith(".ini") and "disabled" not in f.lower():
                ini_files.append(os.path.join(dirpath, f))
        if not scan_subfolders:
            break

    if not ini_files:
        print("⚠️ No eligible .ini files found.")
        wait_for_exit()
        return

    print(f"\n🔍 Found {len(ini_files)} eligible .ini file(s). Previewing changes...")

    files_to_modify = []
    for ini_file in ini_files:
        changed, _ = smart_replace(ini_file, make_backup=make_backup, preview=True)
        if changed:
            files_to_modify.append(ini_file)

    if not files_to_modify:
        print("\nℹ️ No changes needed.")
        wait_for_exit()
        return

    # Final confirmation
    confirm = input(f"\nDo you want to apply changes to {len(files_to_modify)} file(s)? (y/n): ").strip().lower()
    if confirm != "y":
        print("Operation cancelled.")
        wait_for_exit()
        return

    # Apply changes
    files_modified = 0
    for ini_file in files_to_modify:
        changed, _ = smart_replace(ini_file, make_backup=make_backup, preview=False)
        if changed:
            files_modified += 1

    print(f"\n📁 Files processed: {len(ini_files)}")
    print(f"✅ Files modified: {files_modified}")
    print("\n🎉 Finished!")
    wait_for_exit()

def wait_for_exit():
    try:
        input("\nPress ENTER to exit...")
    except EOFError:
        pass

if __name__ == "__main__":
    main()
