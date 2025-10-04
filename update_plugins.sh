#!/bin/bash
# =============================================================================
# Minecraft Plugin Updater - Main Execution Script
# =============================================================================

# Exit immediately if any command fails, preventing partial or corrupt updates.
set -e

# Ensure Python handles UTF-8 correctly, which is important for APIs.
export PYTHONUTF8=1

# --- STEP 1: Load Configuration ---
# Load the directory paths from the config file.
# The script will fail here if config.sh does not exist.
source config.sh
echo "Configuration loaded. Using plugin root: $PLUGIN_DB_ROOT"


# --- STEP 2: Create Directories ---
# Ensure all target directories exist before we start downloading.
# The '-p' flag creates parent directories as needed and doesn't error if they already exist.
echo "Ensuring target directories exist..."
mkdir -p "$AUTOSPIGOT_DIR"
mkdir -p "$VELOCITY_DIR"
mkdir -p "$SPIGOT_DIR"


# --- STEP 3: Download Plugins to Staging Directories ---
# The following section downloads plugins from various sources into the staging directories.
echo "--- Starting plugin downloads into staging directories... ---"

# Download from Jenkins servers (e.g., PaperMC, Empire Minecraft).
./updater/download_jenkins.py --tar "$AUTOSPIGOT_DIR"
./updater/download_jenkins.py --tar "$VELOCITY_DIR"

# Download from Modrinth, a modern platform for Minecraft mods and plugins.
./updater/download_modrinth.py --tar "$AUTOSPIGOT_DIR" --loader paper
./updater/download_modrinth.py --tar "$VELOCITY_DIR" --loader velocity

# Download from Spiget, the unofficial API for SpigotMC resources.
./updater/download_spiget.py --tar "$AUTOSPIGOT_DIR"

# Download plugins from direct URLs using a generic downloader script.
./updater/oget.py https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot -O "$AUTOSPIGOT_DIR/floodgate-spigot.jar"
./updater/oget.py https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot -O "$AUTOSPIGOT_DIR/Geyser-Spigot.jar"

echo "Plugin downloads complete."


# --- STEP 4: Prune Old Versions from Staging Directories ---
# Before syncing, clean up the staging directories by removing older duplicates.
echo "--- Pruning old plugin versions from staging directories... ---"
./updater/pruneDb.py --tar "$AUTOSPIGOT_DIR"
./updater/pruneDb.py --tar "$VELOCITY_DIR"
echo "Pruning complete."


# --- STEP 5: Sync Latest Plugins to Final Database ---
# Use rsync to efficiently copy new and updated files to the final repository.
# The --delete flag ensures that plugins removed from staging are also removed from the final repo.
echo "--- Syncing latest plugins to the final database... ---"
rsync -av --delete "$AUTOSPIGOT_DIR/" "$SPIGOT_DIR/"
echo "Sync complete. The local plugin database is now up-to-date."

