"""Organize files into subfolders using rules from a JSON configuration file."""

import json
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Callable

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


if getattr(sys, "frozen", False):
    CONFIG_FILE = Path(sys.executable).resolve().with_name("config.json")
else:
    CONFIG_FILE = Path(__file__).with_name("config.json")
StatusCallback = Callable[[str], None]
ProgressCallback = Callable[[str, int, int], None]

# These rules are written to config.json automatically the first time the script runs.
# After that, edit config.json to customize the organizer without changing this script.
DEFAULT_SETTINGS = {
    "folder_to_organize": "~/Downloads",
    "organize_existing_files_on_start": True,
    "watch_for_new_files": True,
    "watch_recursive": False,
    "wait_for_file_ready": True,
    "file_ready_checks": 2,
    "file_ready_delay_seconds": 0.5,
    "max_file_ready_attempts": 20,
    "skip_existing_files": True,
}

DEFAULT_CATEGORIES = {
    # Text & Word Processing
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"},
    
    # Financial & Data Sheets
    "Spreadsheets": {".xlsx", ".xls", ".csv", ".ods", ".tsv"},
    
    # Slides & Presentations
    "Presentations": {".pptx", ".ppt", ".odp", ".key"},
    
    # Digital Books
    "EBooks": {".epub", ".mobi", ".azw3", ".djvu"},
    
    # Standard & Raster Visuals
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico", ".tiff", ".heic"},
    
    # Vector Graphic Assets
    "Vectors": {".svg", ".ai", ".eps", ".psd", ".fig", ".xd"},
    
    # Audio & Music Tracks
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".mid"},
    
    # Movies & Video Clips
    "Videos": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    
    # Zip & Compressed Packages
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".iso"},
    
    # Setup Executables
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"},
    
    # Programming Source Code
    "Code": {".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".cs", ".go", ".rs", ".php"},
    
    # Structured Data Configurations
    "Data_Config": {".json", ".xml", ".yaml", ".yml", ".ini", ".toml", ".sql", ".db"},
    
    # Custom System Typography
    "Fonts": {".ttf", ".otf", ".woff", ".woff2", ".eot"}
}






def load_config(
    config_file: Path,
) -> tuple[Path, dict[str, set[str]], dict[str, Any]] | None:
    """Create and read settings and file categories from the JSON config."""
    if not config_file.exists():
        try:
            json_categories = {
                category: sorted(extensions)
                for category, extensions in DEFAULT_CATEGORIES.items()
            }
            default_config = {
                "settings": DEFAULT_SETTINGS,
                "categories": json_categories,
            }
            config_file.write_text(
                json.dumps(default_config, indent=4) + "\n",
                encoding="utf-8",
            )
            print(f"Created default configuration: {config_file}")
        except OSError as error:
            print(f"Could not create configuration file: {error}")
            return None

    try:
        raw_categories = json.loads(config_file.read_text(encoding="utf-8"))
        if not isinstance(raw_categories, dict):
            raise ValueError("the top-level JSON value must be an object")

        raw_settings = raw_categories.get("settings", {})
        raw_category_rules = raw_categories.get("categories", {})
        if not isinstance(raw_settings, dict):
            raise ValueError("settings must be an object")
        if not isinstance(raw_category_rules, dict):
            raise ValueError("categories must be an object")

        settings = dict(DEFAULT_SETTINGS)
        settings.update(raw_settings)

        if not isinstance(settings["folder_to_organize"], str):
            raise ValueError("folder_to_organize must be a string")
        if not settings["folder_to_organize"].strip():
            raise ValueError("folder_to_organize cannot be empty")

        boolean_settings = (
            "organize_existing_files_on_start",
            "watch_for_new_files",
            "watch_recursive",
            "wait_for_file_ready",
            "skip_existing_files",
        )
        if any(not isinstance(settings[name], bool) for name in boolean_settings):
            raise ValueError("watch and organizer options must be true or false")

        integer_settings = ("file_ready_checks", "max_file_ready_attempts")
        if any(
            not isinstance(settings[name], int) or isinstance(settings[name], bool)
            or settings[name] < 1
            for name in integer_settings
        ):
            raise ValueError("file readiness counts must be positive integers")

        if (
            not isinstance(settings["file_ready_delay_seconds"], (int, float))
            or isinstance(settings["file_ready_delay_seconds"], bool)
            or settings["file_ready_delay_seconds"] < 0
        ):
            raise ValueError("file_ready_delay_seconds must be zero or greater")

        categories: dict[str, set[str]] = {}
        for category, extensions in raw_category_rules.items():
            if not isinstance(category, str) or not isinstance(extensions, list):
                raise ValueError("each category must map to a list of extensions")

            if not all(isinstance(extension, str) for extension in extensions):
                raise ValueError("every extension must be a string")

            categories[category] = {extension.lower() for extension in extensions}

        folder = Path(settings["folder_to_organize"]).expanduser()
        return folder, categories, settings
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Could not read configuration file: {error}")
        return None


def category_for_file(
    file_path: Path, file_categories: dict[str, set[str]]
) -> str | None:
    """Return the destination category for a file, or None if it is unknown."""
    extension = file_path.suffix.lower()

    for category, extensions in file_categories.items():
        if extension in extensions:
            return category

    return None


def wait_until_file_is_ready(file_path: Path, settings: dict[str, Any]) -> bool:
    """Wait until a new file's size stops changing before moving it."""
    previous_size = -1
    stable_checks = 0

    for _ in range(settings["max_file_ready_attempts"]):
        try:
            current_size = file_path.stat().st_size
        except OSError:
            time.sleep(settings["file_ready_delay_seconds"])
            continue

        if current_size == previous_size:
            stable_checks += 1
            if stable_checks >= settings["file_ready_checks"]:
                return True
        else:
            previous_size = current_size
            stable_checks = 0

        time.sleep(settings["file_ready_delay_seconds"])

    return False


def organize_file(
    file_path: Path,
    folder: Path,
    file_categories: dict[str, set[str]],
    settings: dict[str, Any],
    config_file: Path | None = None,
    is_new_file: bool = False,
    status_callback: StatusCallback | None = None,
) -> None:
    """Move one recognized file into its configured category folder."""
    if not file_path.is_file():
        return

    if config_file is not None and file_path.resolve() == config_file.resolve():
        report_status(f"Skipped configuration file: {file_path.name}", status_callback)
        return

    category = category_for_file(file_path, file_categories)
    if category is None:
        report_status(f"Skipped unsupported file: {file_path.name}", status_callback)
        return

    destination_folder = folder / category
    destination_file = destination_folder / file_path.name

    try:
        destination_folder.mkdir(exist_ok=True)

        # Never overwrite an existing file with the same name.
        if destination_file.exists() and settings["skip_existing_files"]:
            report_status(
                f"Skipped because it already exists: {destination_file}",
                status_callback,
            )
            return

        if is_new_file and settings["wait_for_file_ready"]:
            if not wait_until_file_is_ready(file_path, settings):
                report_status(
                    f"Could not confirm that {file_path.name} finished downloading",
                    status_callback,
                )
                return

        shutil.move(str(file_path), str(destination_file))
        report_status(
            f"Moved: {file_path.name} -> {category}/{file_path.name}",
            status_callback,
        )
    except OSError as error:
        # A file may be locked, unavailable, or protected by permissions.
        report_status(f"Could not move {file_path.name}: {error}", status_callback)


def organize_folder(
    folder: Path,
    file_categories: dict[str, set[str]],
    settings: dict[str, Any],
    config_file: Path | None = None,
    status_callback: StatusCallback | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Move recognized files from folder into category subfolders."""
    if not folder.exists():
        report_status(f"Folder not found: {folder}", status_callback)
        return

    if not folder.is_dir():
        report_status(f"The path is not a folder: {folder}", status_callback)
        return

    # Make a list first so newly created destination folders are not processed.
    items = list(folder.iterdir())
    file_items = [item for item in items if item.is_file()]
    total_files = len(file_items)
    current_file = 0

    for item in items:
        if not item.is_file():
            report_status(
                f"Skipped directory or non-file: {item.name}", status_callback
            )
            continue

        current_file += 1
        if progress_callback is not None:
            progress_callback("start", current_file, total_files)

        organize_file(
            item,
            folder,
            file_categories,
            settings,
            config_file,
            status_callback=status_callback,
        )

        if progress_callback is not None:
            progress_callback("complete", current_file, total_files)


class DownloadEventHandler(FileSystemEventHandler):
    """Organize files as watchdog reports them in the monitored folder."""

    def __init__(
        self,
        folder: Path,
        file_categories: dict[str, set[str]],
        settings: dict[str, Any],
        config_file: Path,
        status_callback: StatusCallback | None = None,
    ) -> None:
        super().__init__()
        self.folder = folder.resolve()
        self.file_categories = file_categories
        self.settings = settings
        self.config_file = config_file
        self.status_callback = status_callback
        self.destination_folders = {
            (self.folder / category).resolve() for category in file_categories
        }

    def _organize_event_path(self, file_path: Path) -> None:
        resolved_path = file_path.resolve()
        if resolved_path.parent in self.destination_folders:
            return
        if not self.settings["watch_recursive"] and resolved_path.parent != self.folder:
            return
        try:
            resolved_path.relative_to(self.folder)
        except ValueError:
            return

        organize_file(
            resolved_path,
            self.folder,
            self.file_categories,
            self.settings,
            self.config_file,
            is_new_file=True,
            status_callback=self.status_callback,
        )

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._organize_event_path(Path(event.src_path))

    def on_moved(self, event) -> None:
        if not event.is_directory:
            self._organize_event_path(Path(event.dest_path))


def report_status(message: str, status_callback: StatusCallback | None = None) -> None:
    """Send a status message to the GUI when available, otherwise print it."""
    if status_callback is None:
        print(message)
    else:
        status_callback(message)


def create_observer(
    folder: Path,
    file_categories: dict[str, set[str]],
    settings: dict[str, Any],
    config_file: Path,
    status_callback: StatusCallback | None = None,
) -> Any:
    """Create a configured watchdog observer for a folder."""
    event_handler = DownloadEventHandler(
        folder, file_categories, settings, config_file, status_callback
    )
    observer = Observer()
    observer.schedule(
        event_handler,
        str(folder),
        recursive=settings["watch_recursive"],
    )
    return observer


def watch_folder(
    folder: Path,
    file_categories: dict[str, set[str]],
    settings: dict[str, Any],
    config_file: Path,
    status_callback: StatusCallback | None = None,
) -> None:
    """Keep monitoring folder until the user stops the program."""
    observer = create_observer(
        folder,
        file_categories,
        settings,
        config_file,
        status_callback,
    )

    try:
        observer.start()
        report_status(f"Watching for new files in: {folder.resolve()}", status_callback)
        report_status("Press Ctrl+C to stop.", status_callback)
        observer.join()
    except KeyboardInterrupt:
        report_status("Stopping file watcher...", status_callback)
    except OSError as error:
        report_status(f"Could not watch folder: {error}", status_callback)
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    loaded_config = load_config(CONFIG_FILE)
    if loaded_config is not None:
        folder_to_organize, file_categories, settings = loaded_config
        if settings["organize_existing_files_on_start"]:
            organize_folder(
                folder_to_organize,
                file_categories,
                settings,
                CONFIG_FILE,
            )
        if settings["watch_for_new_files"]:
            watch_folder(
                folder_to_organize,
                file_categories,
                settings,
                CONFIG_FILE,
            )
