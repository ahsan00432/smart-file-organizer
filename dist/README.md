# Smart File Organizer for Windows

`SmartFileOrganizer.exe` is a standalone Windows desktop application that organizes files automatically. Python and separate package installation are not required.

## Quick Start

1. Keep `SmartFileOrganizer.exe` and `config.json` in the same folder.
2. Double-click `SmartFileOrganizer.exe`.
3. Use **Browse for folder** to select the folder you want to organize.
4. Click **Clean Folder Now** for a manual cleanup, or enable **Enable Background Live-Monitoring** for automatic organization.

## Features

- Dark-mode graphical interface
- Select any folder with the folder browser
- Manual file organization with **Clean Folder Now**
- Real-time monitoring powered by `watchdog`
- Detects new files and downloaded files automatically
- Waits for files to finish writing before moving them
- Current-file loading bar
- Total-sweep progress bar
- Live activity log for moved, skipped, and failed files
- Avoids overwriting existing files when configured to skip duplicates
- Safely skips locked or inaccessible files
- **Clear System Temp Cache** button for accessible Windows temporary files
- Locked temporary files are skipped during cache cleanup
- **View GitHub Profile** button
- **Rate on GitHub** button
- Branded application icon

## Configuration

Edit `config.json` with a text editor while the application is closed, then start the executable again. The file controls the monitored folder, watcher behavior, download readiness checks, duplicate handling, and extension categories.

Example:

```json
{
    "settings": {
        "folder_to_organize": "C:/Users/YourName/Downloads",
        "organize_existing_files_on_start": true,
        "watch_for_new_files": true,
        "watch_recursive": false,
        "wait_for_file_ready": true,
        "file_ready_checks": 2,
        "file_ready_delay_seconds": 0.5,
        "max_file_ready_attempts": 20,
        "skip_existing_files": true
    },
    "categories": {
        "Documents": [".pdf", ".docx", ".txt"],
        "Images": [".jpg", ".png"],
        "Audio": [".mp3", ".wav"],
        "Archives": [".zip", ".rar", ".7z"]
    }
}
```

### Important Settings

- `folder_to_organize`: Folder monitored and organized by the app. `~/Downloads` means your Windows Downloads folder.
- `organize_existing_files_on_start`: Organize files already present when the app starts.
- `watch_for_new_files`: Enable continuous background monitoring.
- `watch_recursive`: Also monitor files inside subfolders.
- `wait_for_file_ready`: Wait for a downloaded file to stop changing size before moving it.
- `file_ready_checks`: Number of stable size checks required.
- `file_ready_delay_seconds`: Delay between readiness checks.
- `max_file_ready_attempts`: Maximum attempts before a file is skipped.
- `skip_existing_files`: Prevent overwriting a file with the same name.

Category names become destination folder names. For example, a file matching `.zip` in `Archives` is moved to `Archives\\filename.zip`.

## GitHub

Project profile: <https://github.com/ahsan00432>

Use the buttons inside the app to open the GitHub profile and support the project.

## Troubleshooting

- If the app does not start, confirm that Windows has not blocked the downloaded executable.
- If files are not moved, check that `config.json` is beside the executable and contains valid JSON.
- If a file is still downloading or locked, the app waits and then reports it in the activity log.
- Close and reopen the app after changing `config.json`.
- The cache cleanup only removes accessible entries from the Windows temporary folder; files in use are skipped.
