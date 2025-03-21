#!/usr/bin/env python3
"""
Reorganize the flock codebase into a src-based package structure.
This script will:
1. Create a src/flock directory structure
2. Move all Python modules into the src/flock directory
3. Ensure each package has proper __init__.py files
"""
import os
import shutil
import sys
from pathlib import Path

def ensure_dir(path):
    """Ensure a directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)

def ensure_init_file(path):
    """Ensure an __init__.py file exists in a directory."""
    init_file = os.path.join(path, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write(f'"""Flock package: {os.path.basename(path)}"""\n')

def main():
    # Define paths
    current_dir = os.getcwd()
    src_dir = os.path.join(current_dir, "src")
    flock_dir = os.path.join(src_dir, "flock")
    
    # Create initial structure
    ensure_dir(src_dir)
    ensure_dir(flock_dir)
    
    # Create the primary __init__.py file
    with open(os.path.join(flock_dir, "__init__.py"), "w") as f:
        print("Creating main package __init__.py")
        # Copy contents from current __init__.py if it exists
        if os.path.exists(os.path.join(current_dir, "__init__.py")):
            with open(os.path.join(current_dir, "__init__.py"), "r") as old_init:
                f.write(old_init.read())
        else:
            f.write('"""Flock - Agent Framework."""\n\n')
            f.write('from pathlib import Path\n\n')
            f.write('# Define package root\n')
            f.write('PACKAGE_ROOT = Path(__file__).parent\n\n')
            f.write('# Version\n')
            f.write('__version__ = "0.1.0"\n')
    
    # Define packages to move
    packages = [
        "handlers",
        "modular",
        "manifest_utils",
        "type_defs",
        "triframe",
        "utils",
        "workflows",
    ]
    
    # Move each package
    for package in packages:
        if os.path.exists(os.path.join(current_dir, package)):
            print(f"Moving package: {package}")
            dest_dir = os.path.join(flock_dir, package)
            ensure_dir(dest_dir)
            ensure_init_file(dest_dir)
            
            # Copy all files from the package directory
            for item in os.listdir(os.path.join(current_dir, package)):
                src_item = os.path.join(current_dir, package, item)
                dst_item = os.path.join(dest_dir, item)
                
                if os.path.isfile(src_item):
                    shutil.copy2(src_item, dst_item)
                elif os.path.isdir(src_item):
                    # Handle subdirectories (like modular/phases and triframe/phases)
                    subdir = os.path.join(dest_dir, item)
                    ensure_dir(subdir)
                    ensure_init_file(subdir)
                    
                    for subitem in os.listdir(src_item):
                        src_subitem = os.path.join(src_item, subitem)
                        dst_subitem = os.path.join(subdir, subitem)
                        if os.path.isfile(src_subitem):
                            shutil.copy2(src_subitem, dst_subitem)
    
    # Move individual Python modules
    modules = [
        "server.py",
        "operation_handler.py",
        "middleman_client.py",
        "main.py",
        "logger.py",
        "config.py",
        "observation_simulator.py",
    ]
    
    for module in modules:
        if os.path.exists(os.path.join(current_dir, module)):
            print(f"Moving module: {module}")
            shutil.copy2(
                os.path.join(current_dir, module),
                os.path.join(flock_dir, module)
            )
    
    # Create a new main.py in the root directory that imports from the package
    with open(os.path.join(current_dir, "main_src.py"), "w") as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('"""Flock main entry point."""\n\n')
        f.write('from src.flock.main import main\n\n')
        f.write('if __name__ == "__main__":\n')
        f.write('    main()\n')
    
    print("\nReorganization complete!")
    print("\nTo use the reorganized structure:")
    print("1. Run the install script: ./install.py")
    print("2. Test importing the package: python -c 'import src.flock'")
    print("3. Run the application using the new main_src.py instead of main.py")
    print("\nNote: The original files are still in place. After testing that everything works,")
    print("you may want to delete them to avoid confusion.")

if __name__ == "__main__":
    main() 