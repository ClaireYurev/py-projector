import os
import json # not needed but leave for consistency if copying directly
import fnmatch
from datetime import datetime

def read_ignore_patterns(folder_path):
    """Reads ignore patterns from a .pyignore file in the given folder."""
    ignore_file_path = os.path.join(folder_path, ".pyignore")
    if os.path.exists(ignore_file_path):
        with open(ignore_file_path, "r") as f:
            patterns = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return patterns
    return []

def should_ignore(item_path, ignore_patterns, start_folder):
    """Checks if an item should be ignored based on the provided patterns."""
    for pattern in ignore_patterns:
        if pattern.startswith("/"):  # Root-relative pattern
            if fnmatch.fnmatch(os.path.relpath(item_path, start_folder), pattern[1:]):  # Critical that item_path be relative to same starting folder! For directory logic with / to filter as needed
                return True
        elif "*" in pattern or "?" in pattern or "[" in pattern:  # Wildcard pattern anywhere else (other folders non root-relative paths etc., e.g build/*, **/*.tsbuildinfo present inside server/app/* in future etc.)! If *, is used must only work on filename!
            if fnmatch.fnmatch(os.path.basename(item_path), pattern): # Fix to not only get start folder ignored using item_path before should_ignore function rather item alone - otherwise you're doing full filename rather intended relative_directory from current position which causes should_ignore code for / case (with item_path and folder context for directory path comparison with starting scope), here is for non-/ usage so must simply consider itemname matching
                return True
        else:
            if pattern == os.path.basename(item_path):  # Exact name match if specified to skip in root or anywhere (full filenames are also relative to starting/current scope if `/` not at start for directories or for actual non /filename uses) - otherwise fnmatch was causing unintended recursion skips on explicit filenames to ignore in folders outside start
                return True # directory like "node_modules", "out", "*.log"

    return False

def get_file_contents_text(folder_path, output_file, ignore_patterns=None, scanned_count=0, start_folder=None, ignored_files_count=0): # Added ignored_files_count for tracking but not directly used in function now - will be updated in main loop only like prev script example
    """Recursively reads and writes file contents to a text file."""
    if not os.path.exists(folder_path):
        return scanned_count, ignored_files_count # Return counts even on error to prevent issues downstream.

    if ignore_patterns is None:
        ignore_patterns = read_ignore_patterns(folder_path)

    if start_folder is None:
        start_folder = folder_path

    try:
        items = sorted(os.listdir(folder_path))
    except PermissionError:
        print(f"❌ ❌ ❌ Permission denied to access: {folder_path}") # Keep console error output as its useful still in text output as is (also permission problem here may be unexpected given read file action expected to have access!)
        output_file.write(f"// ❌ Permission Denied accessing directory: {folder_path}\n\n") # Add to output log too in case users check txt only in future
        return scanned_count, ignored_files_count

    for item in items:
        item_path = os.path.join(folder_path, item)

        if should_ignore(item_path, ignore_patterns, start_folder):
            # print(f"\rSkipping (ignored): {item}... ", end="") # Optional print skipped items - here too can add output but probably less useful vs prev directory scanner, up to you
            ignored_files_count += 1 # <---- FIX: Increment ignored_files_count HERE inside recursive function
            continue # ignored_files_count += 1 - moved to outer main scope instead only to handle initial top scope items

        scanned_count += 1 # Correct count updated here again too, and fixed count increment/placement/logic - now accurate still due to prev changes

        if os.path.isfile(item_path):
            try: # handle read error too like directory above with perms (or file being deleted during run etc. - robustness still matters for file access unlike directory access earlier - though both relevant for perms etc., or maybe deleted files midway, or network file gone etc.)
                with open(item_path, "r", encoding="utf-8") as infile: # Explicit encoding for broader file type handling (though binary etc will still fail)
                    contents = infile.read()
                output_file.write(f"// Contents of \"{item}\"\n")
                output_file.write(contents)
                output_file.write("\n\n")  # Add spacing between files
            except Exception as e: # Broad exception handling but for file read can be broad but can also narrow if you know file type specific exceptions. Good balance given all files are read text based normally
                print(f"❌ Error reading file: {item_path} - {e}") # again console out error still for quick debug in test runs etc.
                output_file.write(f"// ❌ Error reading file: {item} - {e}\n\n") # Output to file for record keeping and file history as audit/info log too.

        elif os.path.isdir(item_path):
            scanned_count, ignored_files_count = get_file_contents_text( # pass ignored_files_count too even though currently unused in recursive call/inner calls - makes it more clear if future needs update in recursive calls again from base, to pass counts in and out, if its tracked in main for root already, best keep passing here too even if not used inside directly by recursive fn calls right now directly. Consistency matters here.
                item_path, output_file, ignore_patterns, scanned_count, start_folder, ignored_files_count # Propagate file handle and counts to recursive calls. Pass ignored count for completeness if used in future too.
            ) # important: update counts even if only returned but not used by recursive function internally atm.

    return scanned_count, ignored_files_count # Ensure updated counts are returned from recursive level too, though atm only used by main scope for final output now

if __name__ == "__main__":
    target_folder = os.getcwd()

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    output_filename = f"project-file-contents-{date_str}-{time_str}.txt"

    print(f"🚀 Analyzing directory and extracting file contents: {target_folder} ✓")

    ignore_patterns = read_ignore_patterns(target_folder)
    if ignore_patterns:
        print("📗 Loaded '.pyignore' file. These items will be skipped ✓")
    else:
        print("❌ No '.pyignore' file found. Proceeding to process all files. 🔥")

    ignored_files_count = 0 # init ignore count before file read - fixed/updated var logic and placement here too!

    if os.path.isdir(target_folder):
        items_in_target = os.listdir(target_folder)
        for item in items_in_target: # Re-use same outer/root scope check logic/loop from previous script also for consistency too for initial skips at top
            item_path_outer = os.path.join(target_folder, item)
            if should_ignore(item_path_outer, ignore_patterns, target_folder):
                ignored_files_count += 1 # Same outer-scope skip counter logic too, keeping pattern of last script even for different output type - more consistent/less bugs this way across diff script usage, but can simplify or alter in future iterations if needed to avoid redundancy or if scope changes later significantly/needs adjust logic - keeping as close to prev script as logical where makes sense given logic overlap and reuse intent.

        scanned_files = 0 # Reset scanned files count, now this represents ONLY processed file counts not directories too like last time (now directory process is recursive walk, only file content extraction being counted for "scanned_files" output in this new file content extractor script logic now unlike prev script dir-tree JSON writer which counted all items even dirs and files). Script type different, counts also have diff meaning based on output/purpose logic!
        try:
            with open(output_filename, "w", encoding="utf-8") as outfile: # Open file in main scope and pass it down for recursive use in func for efficiency and clear file resource control. Add explicit encoding for write too (consistent and robust file io).
                scanned_files, ignored_files_count = get_file_contents_text( # Pass outfile file handle
                    target_folder, outfile, ignore_patterns=ignore_patterns, scanned_count=0, start_folder=target_folder, ignored_files_count=0 # Pass initial zero for file-scanned counter since its only files now, directory recursion handled separately internally but only file processing here counted at "scanned_files" outer output count value now differently unlike before! Still keep ignored_files_count same from before in outer main scope to track that similar info and meaning still - only scanned is diff due to different core purpose and what 'scanned files' means in new output logic vs old. Consistent names, slightly changed meanings in context of new script.
                )
            print(f"\n📄 File contents saved to: {output_filename}")
        except IOError as e:
            print(f"❌ Error saving to file '{output_filename}': {e}")
        finally:
            print(f"✨ Processed contents of {scanned_files} files, ignored {ignored_files_count} items.") # Updated status line for diff file process count and 'items' is now general term - more descriptive of what's skipped/ignored items vs specific 'files' if dirs too in future - keeps meaning flexible but clear.

    else:
        print(f"❌ Error: '{target_folder}' is not a valid directory.")