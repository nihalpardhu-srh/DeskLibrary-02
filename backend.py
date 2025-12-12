# backend.py - Updated with /stats Route and Screenshot Upload
from flask import Flask, jsonify, request, send_file, send_from_directory
import database 
import sys
import os
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='.', static_url_path='')

# Configure upload folder
UPLOAD_FOLDER = 'screenshots'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

def media_to_json(media_id, media_data):
    """Converts a media dictionary entry into a JSON-serializable format with the ID."""
    item = media_data.copy()
    item['id'] = media_id
    return item

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- SCREENSHOT ENDPOINTS ---

@app.route('/media/<int:media_id>/screenshot', methods=['POST'])
def upload_screenshot(media_id):
    """Upload a screenshot for a media item."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Check if media exists
        if not database.get_media_by_id(media_id):
            return jsonify({'error': f'Media item with ID {media_id} not found'}), 404
        
        # Save file with secure name
        filename = secure_filename(f"media_{media_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Store relative path in database
        screenshot_path = f"screenshots/{filename}"
        database.update_media_screenshot(media_id, screenshot_path)
        
        return jsonify({'message': 'Screenshot uploaded successfully', 'screenshot_path': screenshot_path}), 201
    
    except Exception as e:
        app.logger.error(f"Error uploading screenshot: {e}")
        return jsonify({'error': 'Internal server error occurred while uploading screenshot'}), 500

@app.route('/media/<int:media_id>/screenshot', methods=['GET'])
def get_screenshot_info(media_id):
    """Get screenshot path info for a media item."""
    try:
        screenshot_path = database.get_media_screenshot(media_id)
        if screenshot_path:
            return jsonify({'screenshot_path': screenshot_path, 'has_screenshot': True}), 200
        else:
            return jsonify({'screenshot_path': None, 'has_screenshot': False}), 200
    except Exception as e:
        app.logger.error(f"Error getting screenshot info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/media/<int:media_id>/screenshot', methods=['DELETE'])
def delete_screenshot(media_id):
    """Delete the screenshot for a media item."""
    try:
        screenshot_path = database.get_media_screenshot(media_id)
        
        if screenshot_path and os.path.exists(screenshot_path):
            os.remove(screenshot_path)
        
        database.remove_media_screenshot(media_id)
        return jsonify({'message': 'Screenshot deleted successfully'}), 200
    
    except Exception as e:
        app.logger.error(f"Error deleting screenshot: {e}")
        return jsonify({'error': 'Internal server error occurred while deleting screenshot'}), 500

@app.route('/screenshot/<path:filename>', methods=['GET'])
def serve_screenshot(filename):
    """Serve a screenshot file."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if os.path.exists(file_path):
            return send_file(file_path, mimetype='image/png')
        else:
            return jsonify({'error': 'Screenshot not found'}), 404
    except Exception as e:
        app.logger.error(f"Error serving screenshot: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# --- MEDIA CRUD Endpoints ---

# 1. List all available media items (READ ALL)
@app.route('/')
def serve_index():
    """Serve the main HTML file."""
    return send_from_directory('.', 'index.html')
@app.route('/media', methods=['GET'])
def list_all_media():
    try:
        media_db = database.get_all_media()
        media_list = [media_to_json(id, data) for id, data in media_db.items()]
        return jsonify(media_list)
    except Exception as e:
        app.logger.error(f"Error listing all media: {e}")
        return jsonify({"error": "Internal server error occurred while fetching media."}), 500

# 2. Search/Filter by category
@app.route('/media/category/<category>', methods=['GET'])
def list_media_by_category(category):
    try:
        media_db = database.get_all_media()
        category_media = [
            media_to_json(id, data)
            for id, data in media_db.items()
            if data['category'].lower() == category.lower()
        ]
        return jsonify(category_media)
    except Exception as e:
        app.logger.error(f"Error listing media by category: {e}")
        return jsonify({"error": "Internal server error occurred while filtering media."}), 500

# 3. Search for media items with a specific name (exact match)
@app.route('/media/search', methods=['GET'])
def search_media_by_name():
    name_to_search = request.args.get('name')
    if not name_to_search:
        return jsonify({'error': 'Name parameter is required for search'}), 400

    try:
        media_db = database.get_all_media()
        found_media = []
        for id, data in media_db.items():
            if data['name'].lower() == name_to_search.lower():
                found_media.append(media_to_json(id, data))
                break 

        if found_media:
            return jsonify(found_media)
        else:
            return jsonify([]), 404
    except Exception as e:
        app.logger.error(f"Error searching media: {e}")
        return jsonify({"error": "Internal server error occurred during search."}), 500

# 4. Display the metadata of a specific media item (READ ONE)
@app.route('/media/<int:media_id>', methods=['GET'])
def get_media_metadata(media_id):
    try:
        media_data = database.get_media_by_id(media_id)
        if media_data:
            return jsonify(media_to_json(media_id, media_data))
        else:
            return jsonify({'error': f'Media item with ID {media_id} not found'}), 404
    except Exception as e:
        app.logger.error(f"Error getting media metadata: {e}")
        return jsonify({"error": "Internal server error occurred while fetching metadata."}), 500

# 5. Create a new media item (CREATE)
@app.route('/media', methods=['POST'])
def create_new_media():
    required_fields = ['name', 'publication_date', 'author', 'category']
    if not request.json or not all(key in request.json for key in required_fields):
        return jsonify({'error': f'Missing required fields: {", ".join(required_fields)}'}), 400

    try:
        new_media = {
            'name': request.json['name'],
            'publication_date': request.json['publication_date'],
            'author': request.json['author'],
            'category': request.json['category'] 
        }

        media_id = database.create_media(new_media)
        return jsonify({'message': 'Media item created successfully', 'id': media_id}), 201
    except Exception as e:
        app.logger.error(f"Error creating new media: {e}")
        return jsonify({"error": "Internal server error occurred while creating media."}), 500

# 6. Update an existing media item (UPDATE / EDIT)
@app.route('/media/<int:media_id>', methods=['PUT'])
def update_media_item(media_id):
    required_fields = ['name', 'publication_date', 'author', 'category']
    if not request.json or not all(key in request.json for key in required_fields):
        return jsonify({'error': f'Missing required fields in payload: {", ".join(required_fields)}'}), 400
    
    try:
        updated_data = {
            'name': request.json['name'],
            'publication_date': request.json['publication_date'],
            'author': request.json['author'],
            'category': request.json['category'] 
        }

        if database.update_media(media_id, updated_data):
            return jsonify({'message': f'Media item with ID {media_id} updated successfully'}), 200
        else:
            return jsonify({'error': f'Media item with ID {media_id} not found'}), 404
    except Exception as e:
        app.logger.error(f"Error updating media item: {e}")
        return jsonify({"error": "Internal server error occurred while updating media."}), 500

# 7. Delete a specific media item (DELETE)
@app.route('/media/<int:media_id>', methods=['DELETE'])
def delete_media_item(media_id):
    try:
        if database.delete_media(media_id):
            return jsonify({'message': f'Media item with ID {media_id} deleted successfully'}), 200
        else:
            return jsonify({'error': f'Media item with ID {media_id} not found'}), 404
    except Exception as e:
        app.logger.error(f"Error deleting media item: {e}")
        return jsonify({"error": "Internal server error occurred while deleting media."}), 500

# --- FAVORITES ENDPOINTS (Unchanged) ---
@app.route('/favorites', methods=['GET'])
def list_favorites():
    """Returns a list of all media items that are marked as favorites."""
    try:
        favorite_ids = database.get_favorites()
        media_db = database.get_all_media()
        
        favorite_list = []
        for media_id in favorite_ids:
            if media_id in media_db:
                favorite_list.append(media_to_json(media_id, media_db[media_id]))
        
        return jsonify(favorite_list)
    except Exception as e:
        app.logger.error(f"Error listing favorites: {e}")
        return jsonify({"error": "Internal server error occurred while fetching favorites."}), 500

@app.route('/favorites/ids', methods=['GET'])
def get_favorite_ids():
    """Returns only the list of favorite IDs."""
    try:
        return jsonify({'favorite_ids': database.get_favorites()})
    except Exception as e:
        app.logger.error(f"Error fetching favorite IDs: {e}")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/favorites/add/<int:media_id>', methods=['POST'])
def add_favorite_item(media_id):
    """Adds a media item to the favorites list."""
    try:
        if database.add_favorite(media_id):
            return jsonify({'message': f'Media item {media_id} added to favorites'}), 200
        else:
            return jsonify({'error': 'Media item not found or already a favorite'}), 404
    except Exception as e:
        app.logger.error(f"Error adding favorite: {e}")
        return jsonify({"error": "Internal server error."}), 500

@app.route('/favorites/remove/<int:media_id>', methods=['POST'])
def remove_favorite_item(media_id):
    """Removes a media item from the favorites list."""
    try:
        if database.remove_favorite(media_id):
            return jsonify({'message': f'Media item {media_id} removed from favorites'}), 200
        else:
            return jsonify({'error': 'Media item was not in favorites'}), 404
    except Exception as e:
        app.logger.error(f"Error removing favorite: {e}")
        return jsonify({"error": "Internal server error."}), 500

# --- NEW STATISTICS ENDPOINT ---
@app.route('/stats', methods=['GET'])
def get_statistics():
    """Returns overall media statistics."""
    try:
        stats = database.get_media_statistics()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Error fetching statistics: {e}")
        return jsonify({"error": "Internal server error occurred while fetching statistics."}), 500


# Run the Flask app
if __name__ == '__main__':
    try:
        print("--- Starting Flask Backend Server ---")
        if 'database' not in sys.modules or database.db_store is None:
             print("ERROR: database.py module could not be imported or initialized.")
             database.load_data()
        
        # CRITICAL FIX: Ensure reloader is OFF to prevent global variable corruption
        app.run(debug=True, port=5000, use_reloader=False) 
        
    except Exception as e:
        print(f"FATAL ERROR starting the server: {e}")
        print("Please ensure Flask is installed: 'pip install Flask'")