# database.py - Updated with Statistics Function
import json
import os
from datetime import datetime

DATA_FILE = 'media_data.json'

# Initial data structure remains the same
INITIAL_MEDIA_DATA = {
    "media": {
        1: {
            'name': 'The Martian',
            'publication_date': '2011-09-27',
            'author': 'Andy Weir',
            'category': 'Book',
            'screenshot': None
        },
        2: {
            'name': 'Inception',
            'publication_date': '2010-07-16',
            'author': 'Christopher Nolan',
            'category': 'Film',
            'screenshot': None
        },
        4: {
            'name': 'Dune',
            'publication_date': '1965-08-01',
            'author': 'Frank Herbert',
            'category': 'Book',
            'screenshot': None
        },
        5: {
            'name': 'The Matrix',
            'publication_date': '1999-03-31',
            'author': 'The Wachowskis',
            'category': 'Film',
            'screenshot': None
        }
    },
    "favorites": [] 
}

db_store = None
next_id = 1

def load_data():
    """Loads media data and favorites from the JSON file and safely calculates next_id."""
    global next_id, db_store
    
    if not os.path.exists(DATA_FILE):
        db_store = INITIAL_MEDIA_DATA.copy()
        db_store["media"] = INITIAL_MEDIA_DATA["media"].copy()
        db_store["favorites"] = []
        next_id = max(db_store["media"].keys()) + 1 if db_store["media"] else 1
        save_data(db_store)
        return

    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            media_data = data.get("media", {})
            
            # Convert string keys to integers
            db_store = {
                "media": {int(k): v for k, v in media_data.items()},
                "favorites": [int(fav) if isinstance(fav, str) and fav.isdigit() else fav for fav in data.get("favorites", [])]
            }
            
            if db_store["media"]:
                next_id = max(db_store["media"].keys()) + 1
            else:
                next_id = 1
            
    except json.JSONDecodeError:
        db_store = INITIAL_MEDIA_DATA.copy()
        db_store["media"] = INITIAL_MEDIA_DATA["media"].copy()
        db_store["favorites"] = []
        next_id = max(db_store["media"].keys()) + 1 if db_store["media"] else 1
        save_data(db_store)
    except Exception:
        db_store = INITIAL_MEDIA_DATA.copy()
        db_store["media"] = INITIAL_MEDIA_DATA["media"].copy()
        db_store["favorites"] = []
        next_id = 1

def save_data(data):
    """Saves media data to the JSON file."""
    try:
        with open(DATA_FILE, 'w') as f:
            media_to_save = {str(k): v for k, v in data["media"].items()}
            favorites_to_save = [int(fav) if isinstance(fav, int) else fav for fav in data.get("favorites", [])]
            full_data = {"media": media_to_save, "favorites": favorites_to_save}
            json.dump(full_data, f, indent=4)
    except Exception as e:
        print(f"An error occurred while saving data: {e}")

load_data()

# --- Core CRUD Functions ---
def get_next_id():
    global next_id
    current_id = next_id
    next_id += 1
    return current_id

def get_all_media():
    return db_store["media"]

def get_media_by_id(media_id):
    return db_store["media"].get(media_id)

def create_media(new_media):
    media_id = get_next_id()
    db_store["media"][media_id] = new_media
    save_data(db_store)
    return media_id

def update_media(media_id, updated_data):
    if media_id in db_store["media"]:
        current_data = db_store["media"][media_id]
        current_data.update(updated_data)
        save_data(db_store)
        return True
    return False

def delete_media(media_id):
    if media_id in db_store["media"]:
        del db_store["media"][media_id]
        if media_id in db_store["favorites"]:
            db_store["favorites"].remove(media_id)
        save_data(db_store)
        return True
    return False

# --- Favorites Functions ---
def get_favorites():
    return db_store["favorites"]

def add_favorite(media_id):
    if media_id not in db_store["media"]:
        return False
    if media_id not in db_store["favorites"]:
        db_store["favorites"].append(media_id)
        save_data(db_store)
        return True
    return False

def remove_favorite(media_id):
    if media_id in db_store["favorites"]:
        db_store["favorites"].remove(media_id)
        save_data(db_store)
        return True
    return False

# --- SCREENSHOT FUNCTIONS ---
def update_media_screenshot(media_id, screenshot_path):
    """Updates the screenshot path for a media item."""
    if media_id in db_store["media"]:
        db_store["media"][media_id]['screenshot'] = screenshot_path
        save_data(db_store)
        return True
    return False

def get_media_screenshot(media_id):
    """Gets the screenshot path for a media item."""
    if media_id in db_store["media"]:
        return db_store["media"][media_id].get('screenshot', None)
    return None

def remove_media_screenshot(media_id):
    """Removes the screenshot for a media item."""
    if media_id in db_store["media"]:
        db_store["media"][media_id]['screenshot'] = None
        save_data(db_store)
        return True
    return False

# --- NEW STATISTICS FUNCTION ---
def get_media_statistics():
    """Calculates and returns statistics about the media items."""
    media = db_store["media"]
    stats = {
        'total_items': len(media),
        'total_favorites': len(db_store["favorites"]),
        'categories': {}
    }
    
    # Calculate counts per category
    for item in media.values():
        category = item.get('category', 'Unknown')
        stats['categories'][category] = stats['categories'].get(category, 0) + 1
        
    return stats