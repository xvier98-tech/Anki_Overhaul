# -*- coding: utf-8 -*-
"""
Manager for Tracking and Persisting Recent Images used in Anki Card Editor.
Maintains a Most Recently Used (MRU) list of up to 15 images.
Persists to user_files/recent_images.json and synchronizes with addon configuration.
"""

from typing import List, Dict, Any, Optional
import os
import json
import threading

try:
    from .search_engine import ImageResultItem
except (ImportError, ValueError):
    try:
        from modules.image_search.search_engine import ImageResultItem
    except ImportError:
        from search_engine import ImageResultItem

try:
    from ...utils.config_manager import get_module_config, write_module_config
except (ImportError, ValueError):
    try:
        from utils.config_manager import get_module_config, write_module_config
    except ImportError:
        def get_module_config(mod_name: str) -> Dict[str, Any]:
            return {}
        def write_module_config(mod_name: str, cfg: Dict[str, Any]) -> None:
            pass

MAX_RECENT_IMAGES = 15
_lock = threading.RLock()
_cached_recent: Optional[List[ImageResultItem]] = None


def _get_addon_dir() -> str:
    """Resolves the root directory of the Obsidian Addon."""
    # 1. Traversal from current file: modules/image_search/recent_manager.py -> addon root
    try:
        cur = os.path.dirname(os.path.abspath(__file__))
        parent_mod = os.path.dirname(cur)
        addon_root = os.path.dirname(parent_mod)
        if os.path.exists(os.path.join(addon_root, "manifest.json")) or os.path.exists(os.path.join(addon_root, "config.json")):
            return addon_root
    except Exception:
        pass

    # 2. Check Anki mw addonManager
    try:
        from aqt import mw
        if mw and hasattr(mw, "addonManager"):
            pkg = __name__.split(".")[0]
            fld = mw.addonManager.addonsFolder(pkg)
            if fld and os.path.exists(fld):
                return fld
    except Exception:
        pass

    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_storage_filepath() -> str:
    """Returns absolute path to user_files/recent_images.json."""
    addon_dir = _get_addon_dir()
    user_files = os.path.join(addon_dir, "user_files")
    try:
        os.makedirs(user_files, exist_ok=True)
        return os.path.join(user_files, "recent_images.json")
    except Exception:
        return os.path.join(addon_dir, "recent_images.json")


def item_to_dict(item: ImageResultItem) -> Dict[str, Any]:
    """Converts an ImageResultItem instance into a serializable dict."""
    return {
        "title": getattr(item, "title", ""),
        "thumb_url": getattr(item, "thumb_url", ""),
        "original_url": getattr(item, "original_url", ""),
        "width": getattr(item, "width", 0),
        "height": getattr(item, "height", 0),
        "source": getattr(item, "source", ""),
        "relevance_score": getattr(item, "relevance_score", 0),
    }


def dict_to_item(d: Dict[str, Any]) -> ImageResultItem:
    """Reconstructs an ImageResultItem instance from a dict."""
    return ImageResultItem(
        title=str(d.get("title") or ""),
        thumb_url=str(d.get("thumb_url") or ""),
        original_url=str(d.get("original_url") or ""),
        width=int(d.get("width") or 0),
        height=int(d.get("height") or 0),
        source=str(d.get("source") or ""),
        relevance_score=int(d.get("relevance_score") or 0),
    )


def get_recent_images(max_items: int = MAX_RECENT_IMAGES, force_reload: bool = False) -> List[ImageResultItem]:
    """
    Retrieves the list of most recently used images (up to max_items).
    Returns items in MRU order (newest first).
    """
    global _cached_recent
    with _lock:
        if not force_reload and _cached_recent is not None:
            return list(_cached_recent[:max_items])

        items: List[ImageResultItem] = []
        filepath = _get_storage_filepath()

        # 1. Try reading from dedicated JSON file
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    if isinstance(raw_data, list):
                        for entry in raw_data:
                            if isinstance(entry, dict) and (entry.get("original_url") or entry.get("thumb_url")):
                                items.append(dict_to_item(entry))
            except Exception as e:
                print(f"[RecentImages] Warning reading {filepath}: {e}")

        # 2. Fallback to config_manager if file was empty
        if not items:
            try:
                cfg = get_module_config("image_search")
                recents_cfg = cfg.get("recent_images", [])
                if isinstance(recents_cfg, list):
                    for entry in recents_cfg:
                        if isinstance(entry, dict) and (entry.get("original_url") or entry.get("thumb_url")):
                            items.append(dict_to_item(entry))
            except Exception:
                pass

        _cached_recent = items[:MAX_RECENT_IMAGES]
        return list(_cached_recent[:max_items])


def add_recent_image(item: ImageResultItem) -> None:
    """
    Adds or moves an image to the top (MRU position) of the recent images list.
    Deduplicates by original_url and thumb_url, caps at MAX_RECENT_IMAGES (15),
    and persists both to user_files/recent_images.json and config_manager.
    """
    if not item or (not item.original_url and not item.thumb_url):
        return

    global _cached_recent
    with _lock:
        current = get_recent_images(MAX_RECENT_IMAGES)

        # Deduplicate: remove any existing occurrence matching original_url or thumb_url
        new_list: List[ImageResultItem] = [item]
        target_orig = (item.original_url or "").strip().lower()
        target_thumb = (item.thumb_url or "").strip().lower()

        for existing in current:
            ex_orig = (existing.original_url or "").strip().lower()
            ex_thumb = (existing.thumb_url or "").strip().lower()
            if target_orig and ex_orig == target_orig:
                continue
            if target_thumb and ex_thumb == target_thumb:
                continue
            new_list.append(existing)

        # Cap strictly at MAX_RECENT_IMAGES (15)
        new_list = new_list[:MAX_RECENT_IMAGES]
        _cached_recent = new_list

        # Persist to disk (atomic write)
        filepath = _get_storage_filepath()
        serialized = [item_to_dict(it) for it in new_list]
        try:
            temp_path = f"{filepath}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, ensure_ascii=False, indent=2)
            if os.path.exists(filepath):
                os.replace(temp_path, filepath)
            else:
                os.rename(temp_path, filepath)
        except Exception as e:
            # Fallback direct write
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(serialized, f, ensure_ascii=False, indent=2)
            except Exception as ex:
                print(f"[RecentImages] Error saving recent images: {ex}")

        # Synchronize with config_manager
        try:
            cfg = get_module_config("image_search")
            if isinstance(cfg, dict):
                cfg["recent_images"] = serialized
                write_module_config("image_search", cfg)
        except Exception:
            pass


def clear_recent_images() -> None:
    """Clears all stored recent images."""
    global _cached_recent
    with _lock:
        _cached_recent = []
        filepath = _get_storage_filepath()
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass

        try:
            cfg = get_module_config("image_search")
            if isinstance(cfg, dict):
                cfg["recent_images"] = []
                write_module_config("image_search", cfg)
        except Exception:
            pass
