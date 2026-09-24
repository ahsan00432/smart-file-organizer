# Smart File Organizer

This script watches a configured folder continuously and moves new files into
category folders using the rules in `config.json`. All user-adjustable settings
are in that file.

## Setup

1. Open PowerShell in this project folder.
2. Install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

   You can also install it directly with:

   ```powershell
   python -m pip install watchdog
   ```

3. Review or edit `config.json` to customize the location, watcher behavior,
   readiness timing, duplicate handling, categories, and extensions.
4. Start the organizer:

   ```powershell
   python smart_file_organizer.py
   ```

   Or launch the graphical interface:

   ```powershell
   python organizer_gui.py
   ```

The script first organizes existing files when
`organize_existing_files_on_start` is enabled, then watches for new files when
`watch_for_new_files` is enabled. Press `Ctrl+C` to stop it.

## Windows Executable

The standalone Windows build is available here:

```text
dist\SmartFileOrganizer.exe
```

Double-click the executable to launch the graphical interface. Python and the
project dependencies are not required on the computer running the executable.

Keep `config.json` in the same folder as `SmartFileOrganizer.exe`. The
executable reads this file at startup, so you can customize the monitored
folder, live-monitoring behavior, readiness checks, duplicate handling, and
file categories without rebuilding the application.

The GUI includes:

- Folder selection with a browse button
- `Clean Folder Now` for a manual sweep
- Background live-monitoring powered by `watchdog`
- Current-file and total-sweep progress bars
- Live activity messages for moved, skipped, and failed files
- A `Clear System Temp Cache` action that skips locked files
- `View GitHub Profile` and `Rate on GitHub` buttons
- Branded application icon

To rebuild the executable from source:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyinstaller
python -m PyInstaller --noconfirm --clean --onefile --windowed --icon app_icon.ico --name SmartFileOrganizer organizer_gui.py
```

The rebuilt executable will be placed in `dist\SmartFileOrganizer.exe`.

Example settings:

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
      "Archives": [".zip", ".rar", ".7z"]
   }
}
```