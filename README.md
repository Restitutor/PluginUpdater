# Minecraft Plugin Updater

These scripts fetch the latest versions of Minecraft plugins from multiple sources, organize them into a local database, and prune old versions.

-----

## Features

  * **Multi-Source Downloading**: Pulls plugins from Jenkins, Modrinth, Spiget, and direct URLs.
  * **Staging and Cleanup**: Downloads plugins into temporary staging directories, automatically prunes old versions, and syncs the latest files to a clean, final repository.
  * **Local Repository Management**: Organizes plugins for different server types (e.g., Paper, Velocity) into a central database.
  * **Server Deployment**: Includes dedicated scripts to sync updates from your local database to live server directories and to update the server JAR itself.

-----

## Prerequisites

  * A Unix-like environment (Linux, macOS, WSL).
  * **Bash** shell.
  * **Python 3.x**.
  * **wget** command-line utility.
  * Required Python libraries: `pip install -r requirements.txt`.

-----

## Script Reference

| File | Purpose |
| :--- | :--- |
| `update_plugins.sh` | **Main script**. Automates the entire process of downloading, pruning, and syncing plugins to the local database. |
| `updater/download_jenkins.py` | Downloads the latest JARs from Jenkins CI servers listed in `jenkins.txt`. |
| `updater/download_modrinth.py`| Fetches the latest plugin versions from Modrinth based on `modrinth.csv`. |
| `updater/download_spiget.py` | Downloads plugins from SpigotMC via the Spiget API using resource IDs from `spiget.csv`. |
| `updater/oget.py` | A generic utility to download a file from a direct URL if it has been updated. |
| `updater/pruneDb.py` | Cleans a directory by automatically deleting older versions of the same plugin. |
| `updater/psync.py` | Syncs updated plugins from the local database to a live server's `plugins` folder. |
| `updater/updateServerJar.py` | Downloads the latest stable Paper or Velocity server JAR and removes old versions. |
| `updater/index_plugins.py` | A helper script that extracts metadata (`main`, `version`) from a plugin's `.jar` file. |
| `updater/versions.py` | Provides a `CustomVersion` class for intelligently parsing and comparing complex version strings. |

-----

## Core Concepts

### Directory Strategy

The updater uses a **staging and syncing** strategy to ensure your final plugin repository is always clean and up-to-date.

1.  The `pruneDb.py` script cleans these directories by removing outdated duplicates, leaving only the newest version of each plugin.
2.  The `update_plugins.sh` script uses `rsync` to mirror the cleaned contents of the staging directory (`AUTOSPIGOT_DIR`) into this final repository. This separation ensures that your primary database never contains old or duplicate files.

### Intelligent Version Parsing

Minecraft plugin versioning can be inconsistent (e.g., `1.2.3`, `1.2.3-SNAPSHOT`, `v2.1 (build #15)`). The `versions.py` script uses a `CustomVersion` class to handle this complexity. It intelligently parses these strings by:

  * Stripping non-semantic suffixes like `-SNAPSHOT` or `-Premium`.
  * Extracting core version numbers (`1.2.3`) and build numbers (`.15`).
  * Comparing plugins based on their parsed core version first, and then by other metadata like file modification time if versions are identical.

This ensures that version comparisons are accurate and reliable, which is critical for the pruning and syncing logic.

-----

## 1\. Initial Setup

Before running the scripts, create a configuration file to define your directory structure.

1.  Create a file named `config.sh` in the root of the project.
2.  Copy the contents below into `config.sh` and adjust the paths to your desired setup.

<!-- end list -->

```sh
#!/bin/bash
# -----------------------------------------------------------------------------
# Configuration for the Minecraft Plugin Updater
# -----------------------------------------------------------------------------
# Define the root directory where all plugins will be downloaded and stored.
# By default, this creates a 'plugindb' folder in your home directory.
PLUGIN_DB_ROOT="$HOME/plugindb" 

# --- Subdirectories ---

# Staging directory for newly downloaded Spigot/Paper plugins.
AUTOSPIGOT_DIR="$PLUGIN_DB_ROOT/autospigot"

# Staging directory for newly downloaded Velocity plugins.
VELOCITY_DIR="$PLUGIN_DB_ROOT/velocity" 

# Final repository for active Spigot/Paper plugins.
# The update script syncs the cleaned contents of AUTOSPIGOT_DIR here.
SPIGOT_DIR="$PLUGIN_DB_ROOT/spigot" 
```

-----

## 2\. Configuring Plugin Lists

The downloader scripts read text and CSV files to determine which plugins to fetch. **You must create these configuration files inside the appropriate staging directories** (`$AUTOSPIGOT_DIR` and `$VELOCITY_DIR`).

### Jenkins (`jenkins.txt`)

Place this file in `$AUTOSPIGOT_DIR` and/or `$VELOCITY_DIR`.

  * **Format**: One full Jenkins project URL per line. The script will find the latest successful build.
  * **Example**:
    ```txt
    https://ci.papermc.io/job/Velocity/
    https://ci.emc.gs/job/ChatHandler/
    ```

### Spiget (`spiget.csv`)

Place this file in `$AUTOSPIGOT_DIR`.

  * **Format**: `PluginName,SpigotResourceID`. Find the ID from the SpigotMC resource URL (e.g., for `spigotmc.org/resources/essentialsx.9083/`, the ID is `9083`).
  * **Example**:
    ```csv
    EssentialsX,9083
    ```

### Modrinth (`modrinth.csv`)

Place this file in `$AUTOSPIGOT_DIR` and/or `$VELOCITY_DIR`.

  * The script automatically updates the timestamp after a successful download. Use a placeholder date for new plugins.
  * **Example**:
    ```csv
    luckperms,1970-01-01T00:00:00Z
    ```

-----

## 3\. Usage Workflow

The process involves two main stages: updating your local database and then deploying those changes to your live servers.

### Stage 1: Update Local Plugin Database

It performs the following sequence of actions:

1.  **Downloads**: Fetches the latest plugins from all configured sources (Jenkins, Modrinth, Spiget, etc.) into the staging directories (`$AUTOSPIGOT_DIR`, `$VELOCITY_DIR`).
2.  **Prunes**: Automatically runs `pruneDb.py` on the staging directories to remove older, duplicate plugin versions, ensuring only the newest files remain.
3.  The `--delete` flag ensures the final repo perfectly mirrors the clean staging area.

Simply execute the script to run this entire process:

```sh
./update_plugins.sh
```

For plugins from direct URLs, add `oget.py` commands to `update_plugins.sh`.

  * **Example**:
    ```sh
    # Specify the URL and the output path with -O
    ./updater/oget.py <URL> -O "$AUTOSPIGOT_DIR/plugin-name.jar"
    ```

### Stage 2: Deploy to Servers

Once your local database is up-to-date, you can push the new files to your live servers.

**To Sync Plugins:**
Use the `psync.py` script to copy updated plugins from your final local repository (`$SPIGOT_DIR`) to a server's `plugins` folder. It compares versions and only replaces older files.

  * **Usage**: `updater/psync.py --src <source_dir> --tar <target_dir>`.
  * **Example**:
    ```sh
    # Syncs plugins from your final repo to the server's plugins folder
    # The -y flag confirms all updates without prompting.
    updater/psync.py --src "$SPIGOT_DIR" --tar /path/to/server/plugins -y
    ```

**To Update the Server Jar:**
It automatically finds the latest stable build, downloads it, and removes any old server JARs in the target directory.

  * **Usage**: `updater/updateServerJar.py <type> <version> <path>`.
  * **Example**:
    ```sh
    # Downloads the latest stable Paper 1.21 jar into the server directory
    updater/updateServerJar.py paper 1.21 /path/to/server
    ```
