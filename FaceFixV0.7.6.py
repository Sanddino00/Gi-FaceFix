#!/usr/bin/env python3
import os
import re
import shutil
import sys
import platform
import fnmatch
import logging
import traceback
import concurrent.futures

# ===============================
# FaceFix Utility
# Product: FaceFix
# Version: 0.7.6
# Author: Sanddino
# ===============================

PRODUCT_NAME = "FaceFix"
VERSION = "0.7.6"
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

def smart_replace(file_path, make_backup=True, preview=True, apply_changes=False, process_disabled=False):
    """Scan and optionally replace lines in the file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        lines = content.splitlines(True)
        # Skip DISABLED files unless process_disabled is True
        if "DISABLED" in content and not process_disabled:
            return False, []
            
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

        if apply_changes:
            if make_backup:
                base, _ = os.path.splitext(file_path)
                backup_path = f"{base}_backup.bak"
                shutil.copyfile(file_path, backup_path)
                print(f"💾 Backup saved as '{os.path.relpath(backup_path)}'")

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return True, changed_lines

    except Exception as e:
        logging.exception(f"Error processing '{file_path}'")
        print(f"❌ Error processing '{file_path}': {e}")
        return False, []

def get_exclusion_patterns():
    """Get list of folder names to exclude."""
    # Default pattern to exclude backup files
    patterns = ['*_backup.bak']
    
    print("\nEnter folder names to exclude (press ENTER without input to finish):")
    print("Examples: 'backup' or 'SubFolder'")
    print("Note: Entering a folder name will exclude the entire folder and its contents")
    print("Note: '*_backup.bak' files are automatically excluded")
    
    while True:
        folder_name = input("Folder to exclude (or ENTER to continue): ").strip()
        if not folder_name:
            break
        # Convert folder name to pattern that matches the folder anywhere in path
        patterns.append(f"*{folder_name}*")
    return patterns


def setup_logging(log_path=None):
    """Configure logging to file and stdout."""
    if not log_path:
        log_path = os.path.join(os.getcwd(), f"{PRODUCT_NAME}.log")
    # BasicConfig will be ignored if root handlers already configured in frozen exe; guard with try
    try:
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s %(levelname)s: %(message)s",
                            handlers=[logging.FileHandler(log_path, encoding='utf-8'),
                                      logging.StreamHandler(sys.stdout)])
    except Exception:
        # Fallback: configure a simple stream handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
        logging.getLogger().addHandler(handler)
    logging.info(f"{PRODUCT_NAME} v{VERSION} started")

def is_disabled_file(file_path):
    """Check if file is disabled by filename or content.

    Returns True if the filename contains the word 'disabled' (case-insensitive)
    or the file contents include the marker 'DISABLED'. This makes the
    behavior consistent for files named like 'DISABLEDSayu.ini'.
    """
    try:
        # Fast check: filename contains 'disabled'
        try:
            if 'disabled' in os.path.basename(file_path).lower():
                return True
        except Exception:
            # If something odd with the path, fall through to content check
            pass

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
            except Exception:
                return False
            return 'DISABLED' in content
    except Exception:
        return False

def should_exclude(path, exclusion_patterns):
    """Check if path matches any excluded folder."""
    if not exclusion_patterns:  # Handle case when no patterns are provided
        return False
        
    path = path.replace('\\', '/')  # Normalize path separators
    for pattern in exclusion_patterns:
        if pattern.endswith('.bak'):  # Special handling for backup files
            if fnmatch.fnmatch(path.lower(), pattern.lower()):
                return True
        else:  # For folders, check if pattern exists in path
            if pattern.strip('*').lower() in path.lower():
                return True
    return False

def main():
    setup_logging()
    logging.info(f"{PRODUCT_NAME} v{VERSION} — by {AUTHOR}")
    print(f"{PRODUCT_NAME} v{VERSION} — by {AUTHOR}\n")

    make_backup = True
    if "-nobackup" in [arg.lower() for arg in sys.argv[1:]]:
        make_backup = False

    # Use the current working directory instead of script location
    folder = os.getcwd()
    print(f"Working directory: {folder}")

    process_disabled = input("Process disabled files? (Y/N): ").strip().lower() == 'y'
    
    scan_subfolders = input("Scan subfolders? (Y/N): ").strip().lower() == 'y'

    print("\nYour choices:")
    print(f"• Process disabled files: {'Yes' if process_disabled else 'No'}")
    print(f"• Scan subfolders: {'Yes' if scan_subfolders else 'No'}")
    
    confirm = input("\nAre these settings correct? (Y/N): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        wait_for_exit()
        return

    # Get exclusion patterns
    exclusion_patterns = get_exclusion_patterns()

    # Collect .ini files
    ini_files = []
    try:
        for dirpath, _, filenames in os.walk(folder):
            rel_path = os.path.relpath(dirpath, folder).replace('\\', '/')
            if should_exclude(rel_path, exclusion_patterns):
                continue

            for f in filenames:
                if not f.lower().endswith('.ini'):
                    continue

                file_path = os.path.join(dirpath, f)
                rel_file_path = os.path.relpath(file_path, folder).replace('\\', '/')

                if should_exclude(rel_file_path, exclusion_patterns):
                    continue

                try:
                    is_disabled = is_disabled_file(file_path)
                    if is_disabled:
                        if process_disabled:
                            ini_files.append(file_path)
                            print(f"ℹ️ Including disabled file: {rel_file_path}")
                        else:
                            print(f"⚠️ Skipping disabled file: {rel_file_path}")
                    else:
                        ini_files.append(file_path)
                except Exception:
                    logging.exception(f"Failed to inspect file: {file_path}")
                    # If we can't read the file metadata, skip it
                    continue

            if not scan_subfolders:
                break
    except Exception as e:
        logging.exception("Error walking directories")
        print(f"❌ Error scanning folders: {e}")

    if not ini_files:
        print("⚠️ No eligible .ini files found.")
        wait_for_exit()
        return

    print(f"\n🔍 Found {len(ini_files)} eligible .ini file(s). Previewing changes...")

    files_to_modify = []
    for ini_file in ini_files:
        try:
            changed, _ = smart_replace(ini_file, make_backup=make_backup, preview=True, process_disabled=process_disabled)
            if changed:
                files_to_modify.append(ini_file)
        except Exception as e:
            logging.exception(f"Preview failed for {ini_file}")
            print(f"❌ Error previewing '{os.path.relpath(ini_file)}': {e}")

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

    # Apply changes (use a thread pool to avoid long sequential blocking on many files)
    files_modified = 0
    # Determine max workers from CLI --workers=N or env FACEFIX_WORKERS
    max_workers = None
    for arg in sys.argv[1:]:
        if arg.lower().startswith("--workers="):
            try:
                max_workers = int(arg.split('=', 1)[1])
            except Exception:
                pass
    if not max_workers:
        try:
            max_workers = min(32, (os.cpu_count() or 1) + 4)
        except Exception:
            max_workers = 4

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(smart_replace, ini_file, make_backup, False, True, process_disabled): ini_file for ini_file in files_to_modify}
        for fut in concurrent.futures.as_completed(future_to_file):
            ini_file = future_to_file[fut]
            try:
                changed, _ = fut.result()
                if changed:
                    files_modified += 1
            except Exception as e:
                logging.exception(f"Failed to apply changes to {ini_file}")
                print(f"❌ Error applying changes to '{os.path.relpath(ini_file)}': {e}")

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
