"""Manages offboard (USB) configuration loading"""
import fs
import fs.base
import os
from utils import config_dir, plugins_dir, profiles_dir, root_dir
import time

SCAN_FOR_DIR: str = "multifx"

# Scans for a test directory under gui root when true
MOCK = False

# USB directory and fallbacks
USB_DIRS = [f"/run/media/{os.getlogin()}", f"/media/{os.getlogin()}"]
if MOCK:
    USB_DIRS = [f"{root_dir}/.mockdev"]

PROFILES_FOLDER = os.path.basename(profiles_dir)
PLUGINS_FOLDER = os.path.basename(plugins_dir)


def scan_devices() -> fs.base.FS | None:
    """
    Scan for media drives, then returns the first directory that contains
    SCAN_FOR_DIR
    """
    for USB_DIR in USB_DIRS:
        try:
            dev_fs = fs.open_fs(USB_DIR)
            for dir in dev_fs.scandir(""):
                # Skip files
                if not dir.is_dir:
                    continue
                print(f"Checking {USB_DIR}/{dir.name} for {SCAN_FOR_DIR}")
                for final_dir in dev_fs.filterdir(dir.name, dirs=[SCAN_FOR_DIR]):
                    if not final_dir.is_dir:
                        break
                    print(f"{SCAN_FOR_DIR} found in {dir.name}!")
                    return fs.open_fs(f"{USB_DIR}/{dir.name}/{SCAN_FOR_DIR}")
                print(f"{SCAN_FOR_DIR} directory not found in {USB_DIR}/{dir.name}")
            return None
        except fs.errors.CreateFailed:
            continue


def try_load() -> bool:
    """
    Attempts to load data from a USB, returns True if successful
    """
    extcfg_fs = scan_devices()
    if not extcfg_fs:
        return False
    incfg_fs = fs.open_fs(config_dir)

    migrate_flat_layout(extcfg_fs)
    migrate_flat_layout(incfg_fs)

    copy_subdir(extcfg_fs, incfg_fs, PROFILES_FOLDER)
    copy_subdir(extcfg_fs, incfg_fs, PLUGINS_FOLDER)

    return True


def try_save() -> bool:
    """
    Attempts to write on-board data to a USB, returns True if successful
    """
    extcfg_fs = scan_devices()
    if not extcfg_fs:
        time.sleep(1)  # simulate saving
        return False
    incfg_fs = fs.open_fs(config_dir)

    migrate_flat_layout(extcfg_fs)
    migrate_flat_layout(incfg_fs)

    copy_subdir(incfg_fs, extcfg_fs, PROFILES_FOLDER)
    copy_subdir(incfg_fs, extcfg_fs, PLUGINS_FOLDER)

    return True


def migrate_flat_layout(target_fs: fs.base.FS) -> None:
    """Ensure the new profiles/plugins layout exists, migrating flat files if needed."""

    has_profiles = target_fs.exists(PROFILES_FOLDER)
    has_plugins = target_fs.exists(PLUGINS_FOLDER)

    if not has_profiles and not has_plugins:
        for entry in list(target_fs.scandir("")):
            if entry.is_dir:
                continue
            dest_dir = PROFILES_FOLDER if entry.name.lower().endswith(".json") else PLUGINS_FOLDER
            if not target_fs.exists(dest_dir):
                target_fs.makedir(dest_dir, recreate=True)
            target_fs.move(entry.name, f"{dest_dir}/{entry.name}")
        has_profiles = target_fs.exists(PROFILES_FOLDER)
        has_plugins = target_fs.exists(PLUGINS_FOLDER)

    if not has_profiles:
        target_fs.makedir(PROFILES_FOLDER, recreate=True)
    if not has_plugins:
        target_fs.makedir(PLUGINS_FOLDER, recreate=True)


def copy_subdir(src_fs: fs.base.FS, dest_fs: fs.base.FS, subdir: str) -> None:
    """Replace a destination subdirectory with contents from the source if present."""

    if dest_fs.exists(subdir):
        if dest_fs.isdir(subdir):
            dest_fs.removetree(subdir)
        else:
            dest_fs.remove(subdir)
    dest_fs.makedir(subdir, recreate=True)

    if src_fs.exists(subdir):
        fs.copy.copy_dir(src_fs, subdir, dest_fs, subdir)
