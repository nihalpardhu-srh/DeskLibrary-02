# frontend.py - Updated with Statistics Panel and Publication Year
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from datetime import datetime
from PIL import Image, ImageTk
import io

# Base URL for the Flask backend (MUST match the running server address)
BASE_URL = "http://127.0.0.1:5000"

# --- Modern Color Palette ---
COLOR_PRIMARY = "#4A90E2"  # Blue for accents
COLOR_SECONDARY = "#50C479" # Green for success/create button
COLOR_BG_LIGHT = "#F4F7F6" # Light gray for background
COLOR_TEXT_DARK = "#333333" # Dark gray for text
COLOR_HEADER_BG = "#2C3E50" # Dark slate for header background
COLOR_HEADER_TEXT = "white"
COLOR_FAVORITES = "#FFD700" # Gold for favorites actions
COLOR_EDIT = "#FF8C00" # Dark Orange for Edit
COLOR_STATS_BG = "#E0E6E9" # Light background for stats

class LibraryDeskApp:
    def __init__(self, master):
        self.master = master
        master.title("📚 Library Desk") 
        master.geometry("1100x750") 
        master.config(bg=COLOR_BG_LIGHT)
        
        # --- Theme and Style Configuration ---
        style = ttk.Style()
        style.theme_use('clam') 
        style.configure('TFrame', background=COLOR_BG_LIGHT)
        style.configure('TLabel', background=COLOR_BG_LIGHT, foreground=COLOR_TEXT_DARK)
        
        style.configure('Danger.TButton', foreground='white', background='#dc3545', font=('Segoe UI', 10, 'bold'))
        style.map('Danger.TButton', background=[('active', '#c82333'), ('disabled', 'lightgrey')], foreground=[('disabled', 'grey')])
        
        style.configure('Accent.TButton', foreground='white', background=COLOR_SECONDARY, font=('Segoe UI', 10, 'bold'))
        style.map('Accent.TButton', background=[('active', '#45A96A'), ('disabled', 'lightgrey')], foreground=[('disabled', 'grey')])

        style.configure('Edit.TButton', foreground='white', background=COLOR_EDIT, font=('Segoe UI', 10, 'bold'))
        style.map('Edit.TButton', background=[('active', '#E57300'), ('disabled', 'lightgrey')], foreground=[('disabled', 'grey')])
        
        style.configure('Header.TLabel', background=COLOR_HEADER_BG, foreground=COLOR_HEADER_TEXT, font=('Segoe UI', 18, 'bold'))
        
        # Treeview style for columns
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'), background=COLOR_PRIMARY, foreground='white')
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=25)
        style.map("Treeview", background=[('selected', COLOR_PRIMARY)], foreground=[('selected', 'white')])

        self.categories = ["All", "Book", "Film", "Magazine"]
        self.current_media_list = []
        self.current_selected_item = None 
        self.current_selected_id = None 
        self.favorites_list = []
        self.stats_labels = {} # Dictionary to hold statistic labels

        # --- HEADER ---
        header_frame = ttk.Frame(master, padding="15 10 15 10", style='Header.TLabel')
        header_frame.pack(fill=tk.X, anchor=tk.N)
        
        ttk.Label(header_frame, text="📚 LIBRARY DESK", style='Header.TLabel', font=('Segoe UI', 18, 'bold')).pack(side=tk.LEFT)
        
        # --- Main Content Layout ---
        main_panedwindow = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        main_panedwindow.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- LEFT PANEL (List and Controls) ---
        list_panel = ttk.Frame(main_panedwindow, padding="15", relief=tk.FLAT, borderwidth=1)
        list_panel.columnconfigure(0, weight=1)
        list_panel.rowconfigure(2, weight=1)
        main_panedwindow.add(list_panel, weight=3)

        # 1. Control Bar (Filter, Refresh, and Create)
        control_frame = ttk.Frame(list_panel)
        control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        control_frame.columnconfigure(0, weight=1)
        
        button_group_frame = ttk.Frame(control_frame)
        button_group_frame.grid(row=0, column=0, sticky="e")
        
        ttk.Button(button_group_frame, text="🔄 Refresh All", command=self.refresh_data, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_group_frame, text="⭐ Show Favorites", command=self.load_favorites, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_group_frame, text="➕ Create New Media", command=self.open_create_dialog, style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        # 2. Search & Filter
        search_filter_frame = ttk.Frame(list_panel)
        search_filter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search_filter_frame.columnconfigure(3, weight=1)

        ttk.Label(search_filter_frame, text="Filter:").grid(row=0, column=0, padx=5, sticky="w")
        self.category_var = tk.StringVar(search_filter_frame)
        self.category_var.set(self.categories[0])
        self.category_var.trace_add("write", lambda name, index, mode: self.load_media_by_category())
        
        radio_frame = ttk.Frame(search_filter_frame)
        radio_frame.grid(row=0, column=1, padx=5, sticky="w")
        
        for i, category in enumerate(self.categories):
            radio = ttk.Radiobutton(radio_frame, text=category, variable=self.category_var, value=category)
            radio.pack(side=tk.LEFT, padx=5)

        ttk.Label(search_filter_frame, text="Search:").grid(row=0, column=2, padx=(20, 5), sticky="w")
        self.search_entry = ttk.Entry(search_filter_frame, font=('Segoe UI', 10))
        self.search_entry.grid(row=0, column=3, padx=5, sticky="ew")
        ttk.Button(search_filter_frame, text="🔍", width=3, command=self.search_media_by_name).grid(row=0, column=4, padx=5)

        # 3. Media List (Treeview with Columns)
        treeview_frame = ttk.Frame(list_panel)
        treeview_frame.grid(row=2, column=0, sticky="nsew")
        treeview_frame.columnconfigure(0, weight=1)
        treeview_frame.rowconfigure(0, weight=1)

        # --- Columns updated: Removed 'ID', added 'Year' ---
        columns = ('HiddenID', 'Year', 'Category', 'Name') 
        self.media_tree = ttk.Treeview(treeview_frame, columns=columns, show='headings', selectmode='browse')
        
        # We hide the ID column but keep it in the tuple for internal use
        self.media_tree.column('HiddenID', width=0, stretch=tk.NO)
        self.media_tree.heading('HiddenID', text='', anchor='w')

        self.media_tree.heading('Year', text='Year', anchor='w')
        self.media_tree.column('Year', width=60, anchor='w')
        self.media_tree.heading('Category', text='Category', anchor='w')
        self.media_tree.column('Category', width=100, anchor='w')
        self.media_tree.heading('Name', text='Title / Name', anchor='w')
        self.media_tree.column('Name', width=350, anchor='w')
        
        self.media_tree.grid(row=0, column=0, sticky="nsew")
        self.media_tree.bind('<<TreeviewSelect>>', self.display_metadata_from_tree) 
        
        scrollbar = ttk.Scrollbar(treeview_frame, orient=tk.VERTICAL, command=self.media_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.media_tree.config(yscrollcommand=scrollbar.set)
        
        # --- RIGHT PANEL (Statistics and Details) ---
        right_panel = ttk.Frame(main_panedwindow, padding="15", style='TFrame')
        right_panel.columnconfigure(0, weight=1)
        main_panedwindow.add(right_panel, weight=2)
        
        # 4. Statistics Panel (Always Visible)
        stats_frame = ttk.Frame(right_panel, padding="15", relief=tk.RAISED, borderwidth=1, style='TFrame')
        stats_frame.grid(row=0, column=0, sticky='new', pady=(0, 20))
        stats_frame.columnconfigure(1, weight=1)

        ttk.Label(stats_frame, text="📊 LIBRARY STATISTICS", font=('Segoe UI', 14, 'bold'), foreground=COLOR_SECONDARY).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')
        
        stats_fields = ['Total Items', 'Total Books', 'Total Films', 'Total Magazines', 'Total Favorites']
        
        for i, field in enumerate(stats_fields):
            ttk.Label(stats_frame, text=f"{field}:", font=('Segoe UI', 11, 'bold')).grid(row=i+1, column=0, padx=5, pady=3, sticky='w')
            label = ttk.Label(stats_frame, text="---", font=('Segoe UI', 11), foreground=COLOR_PRIMARY)
            label.grid(row=i+1, column=1, padx=5, pady=3, sticky='w')
            self.stats_labels[field] = label
            
        ttk.Separator(right_panel, orient='horizontal').grid(row=1, column=0, sticky='ew', pady=10)

        # 5. Details Panel (Shows Selected Item)
        detail_panel = ttk.Frame(right_panel, padding="0", style='TFrame')
        detail_panel.grid(row=2, column=0, sticky='new')
        detail_panel.columnconfigure(1, weight=1)
        
        ttk.Label(detail_panel, text="📌 Media Details", font=('Segoe UI', 14, 'bold', 'underline'), foreground=COLOR_PRIMARY).grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky='w')
        
        self.detail_labels = {}
        fields = ['ID', 'Name', 'Author', 'Category', 'Publication Date']
        
        for i, field in enumerate(fields):
            ttk.Label(detail_panel, text=f"{field}:", font=('Segoe UI', 11, 'bold')).grid(row=i+1, column=0, padx=5, pady=7, sticky='w')
            
            label = ttk.Label(detail_panel, text="---", font=('Segoe UI', 11), foreground=COLOR_TEXT_DARK, wraplength=350, justify=tk.LEFT)
            label.grid(row=i+1, column=1, padx=5, pady=7, sticky='ew')
            self.detail_labels[field] = label
        
        ttk.Separator(detail_panel, orient='horizontal').grid(row=len(fields)+1, column=0, columnspan=2, sticky='ew', pady=20)

        # Action Buttons (Delete, Favorites Toggle, Edit, and Screenshot)
        action_button_frame = ttk.Frame(detail_panel)
        action_button_frame.grid(row=len(fields)+2, column=0, columnspan=2, sticky='e')
        
        self.delete_button = ttk.Button(action_button_frame, text="🗑️ Delete Media", command=self.delete_media, style='Danger.TButton', state=tk.DISABLED)
        self.delete_button.pack(side=tk.RIGHT, padx=5)
        
        self.favorites_button = ttk.Button(action_button_frame, text="⭐ Add to Favorites", command=self.toggle_favorite, style='Accent.TButton', state=tk.DISABLED)
        self.favorites_button.pack(side=tk.RIGHT, padx=5)
        
        self.edit_button = ttk.Button(action_button_frame, text="✏️ Edit Media", command=self.open_edit_dialog, style='Edit.TButton', state=tk.DISABLED)
        self.edit_button.pack(side=tk.RIGHT, padx=5)

        # (Screenshot buttons removed)
        
        # --- Initial Load ---
        self.update_favorites_list()
        self.load_all_media()
        self.load_statistics() # Load stats initially
        self.clear_metadata_display()

    # --- Core Application Logic ---

    def refresh_data(self):
        """Refreshes the favorites list, statistics, and reloads all media."""
        self.update_favorites_list()
        self.load_statistics()
        self.load_all_media()
        messagebox.showinfo("Refresh", "Data reloaded and synchronized with backend.")

    def _get_media(self, url):
        """Generic GET request to the backend with robust error handling."""
        try:
            response = requests.get(url)
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", 
                                 f"Failed to connect to backend at {BASE_URL}.\n"
                                 "Please ensure 'backend.py' is running in a separate terminal.")
            return []
        except requests.exceptions.HTTPError as e:
            error_message = f"Server Error: {e.response.status_code} {e.response.reason}"
            try:
                error_data = e.response.json()
                error_message = error_data.get('error', error_data.get('message', error_message))
            except:
                pass 
            if e.response.status_code == 404:
                return [] 
            messagebox.showerror("HTTP Error", error_message)
            return []
        except Exception as e:
            messagebox.showerror("Request Error", f"An unexpected error occurred during GET request: {e}")
            return []
            
    def _post_put_delete_favorite(self, url, method='POST', json_data=None):
        """Generic POST, PUT, DELETE request."""
        try:
            if method == 'POST':
                response = requests.post(url, json=json_data)
            elif method == 'PUT':
                response = requests.put(url, json=json_data)
            elif method == 'DELETE':
                response = requests.delete(url)
            elif method == 'GET': # Used for fetching single item details
                 response = requests.get(url)
            else:
                raise ValueError("Invalid HTTP method specified.")
                
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.RequestException as e:
            error_message = f"Failed to perform action: {e}"
            try:
                error_message = e.response.json().get('error', error_message)
            except:
                pass
            if method != 'GET':
                 messagebox.showerror("Action Error", error_message)
            return False, None

    # --- Statistics Logic ---
    def load_statistics(self):
        """Fetches and displays library statistics."""
        stats = self._get_media(f"{BASE_URL}/stats")
        
        if stats and isinstance(stats, dict):
            self.stats_labels['Total Items'].config(text=stats.get('total_items', 0))
            self.stats_labels['Total Favorites'].config(text=stats.get('total_favorites', 0))
            
            # Update category specific stats, defaulting to 0 if category is missing
            self.stats_labels['Total Books'].config(text=stats['categories'].get('Book', 0))
            self.stats_labels['Total Films'].config(text=stats['categories'].get('Film', 0))
            self.stats_labels['Total Magazines'].config(text=stats['categories'].get('Magazine', 0))
        else:
             for label in self.stats_labels.values():
                 label.config(text="N/A")

    # --- Data Loading and Filtering ---
    def load_all_media(self):
        self.category_var.set("All")
        data = self._get_media(f"{BASE_URL}/media")
        self.update_treeview(data)
        self.load_statistics()

    def load_media_by_category(self):
        category = self.category_var.get()
        if category == "All":
            self.load_all_media()
            return
        
        data = self._get_media(f"{BASE_URL}/media/category/{category}")
        self.update_treeview(data)

    def load_favorites(self):
        self.category_var.set("All")
        data = self._get_media(f"{BASE_URL}/favorites")
        self.update_treeview(data)
        if data:
            messagebox.showinfo("Favorites", "Displaying your favorite items.")
        else:
             messagebox.showinfo("Favorites", "Your favorites list is empty.")
             
    def search_media_by_name(self):
        search_name = self.search_entry.get().strip()
        if not search_name:
            self.load_all_media()
            return

        url = f"{BASE_URL}/media/search?name={search_name}"
        data = self._get_media(url)
        
        self.update_treeview(data)
        if not data:
             messagebox.showinfo("Search Result", f"No media found with exact name: '{search_name}'.")

    # --- Favorites Logic ---
    def update_favorites_list(self):
        try:
            response = requests.get(f"{BASE_URL}/favorites/ids")
            response.raise_for_status()
            self.favorites_list = response.json().get('favorite_ids', [])
        except requests.exceptions.RequestException:
            self.favorites_list = []

    def toggle_favorite(self):
        media_id = self.current_selected_id
        if not media_id:
            return

        if media_id in self.favorites_list:
            success, _ = self._post_put_delete_favorite(f"{BASE_URL}/favorites/remove/{media_id}")
            if success:
                messagebox.showinfo("Favorites", f"Item (ID: {media_id}) removed from favorites.")
        else:
            success, _ = self._post_put_delete_favorite(f"{BASE_URL}/favorites/add/{media_id}")
            if success:
                messagebox.showinfo("Favorites", f"Item (ID: {media_id}) added to favorites.")
        
        if success:
            self.update_favorites_list()
            self.load_statistics() # Update stats after favorite action
            self._update_favorites_button_text()


    # --- GUI Update Methods ---
    def _extract_year(self, date_str):
        """Helper to extract year from YYYY-MM-DD date string."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').year
        except ValueError:
            return 'N/A'

    def update_treeview(self, media_list):
        for item in self.media_tree.get_children():
            self.media_tree.delete(item)
            
        self.current_media_list = media_list
        
        if not media_list:
             self.clear_metadata_display()
             return

        for media in media_list:
            # We now pass (ID, Year, Category, Name) to the treeview
            year = self._extract_year(media.get('publication_date', ''))
            self.media_tree.insert('', tk.END, 
                                   values=(media['id'], year, media['category'], media['name']))
            
        if media_list:
            first_item = self.media_tree.get_children()[0]
            self.media_tree.selection_set(first_item)
            self.display_metadata_from_tree(None)

    def clear_metadata_display(self):
        for label in self.detail_labels.values():
            label.config(text="---", foreground=COLOR_TEXT_DARK) 
        self.delete_button.config(state=tk.DISABLED)
        self.favorites_button.config(state=tk.DISABLED, text="⭐ Add to Favorites")
        self.edit_button.config(state=tk.DISABLED)
        self.current_selected_id = None
        self.current_selected_item = None

    def _update_favorites_button_text(self):
        media_id = self.current_selected_id
        if media_id and media_id in self.favorites_list:
            self.favorites_button.config(text="❌ Remove from Favorites", style='Danger.TButton')
        else:
            self.favorites_button.config(text="⭐ Add to Favorites", style='Accent.TButton')
            
    def display_metadata_from_tree(self, event):
        selected_items = self.media_tree.selection()
        if not selected_items:
            self.clear_metadata_display()
            return 

        self.current_selected_item = selected_items[0]
        # Get all values, including the hidden ID (first element)
        row_values = self.media_tree.item(self.current_selected_item, 'values') 
        
        if not row_values:
            self.clear_metadata_display()
            return

        # ID is row_values[0]
        media_id = int(row_values[0])
        selected_media = next((media for media in self.current_media_list if media['id'] == media_id), None)
        
        if not selected_media:
            self.clear_metadata_display()
            return

        self.current_selected_id = media_id
        
        # Update details panel
        self.detail_labels['ID'].config(text=str(selected_media.get('id', 'N/A')), foreground=COLOR_TEXT_DARK)
        self.detail_labels['Name'].config(text=selected_media.get('name', 'N/A'), foreground=COLOR_TEXT_DARK)
        self.detail_labels['Author'].config(text=selected_media.get('author', 'N/A'), foreground=COLOR_TEXT_DARK)
        self.detail_labels['Category'].config(text=selected_media.get('category', 'N/A'), foreground=COLOR_TEXT_DARK)
        self.detail_labels['Publication Date'].config(text=selected_media.get('publication_date', 'N/A'), foreground=COLOR_TEXT_DARK)
        
        # Enable action buttons
        self.delete_button.config(state=tk.NORMAL)
        self.favorites_button.config(state=tk.NORMAL)
        self.edit_button.config(state=tk.NORMAL)
        self._update_favorites_button_text()


    # --- CRUD Operations ---
    
    def open_create_dialog(self):
        self._open_crud_dialog(is_create=True)
        
    def open_edit_dialog(self):
        if self.current_selected_id is None:
            messagebox.showwarning("Selection Error", "Please select a media item to edit.")
            return

        media_id = self.current_selected_id
        url = f"{BASE_URL}/media/{media_id}"
        
        # Fetch current data to pre-fill
        success, response_data = self._post_put_delete_favorite(url, method='GET')
        
        if success and response_data and isinstance(response_data, dict):
            self._open_crud_dialog(is_create=False, media_data=response_data)
        else:
             messagebox.showerror("Error", f"Could not fetch data for editing Media ID: {media_id}")

    def _open_crud_dialog(self, is_create=True, media_data=None):
        """Generalized dialog for both Create and Edit."""
        dialog = tk.Toplevel(self.master)
        if is_create:
            title_text = '➕ Create New'
        else:
            title_text = f"✏️ Edit Media ID: {media_data.get('id', 'N/A')}"
        dialog.title(title_text)
        dialog.transient(self.master)
        dialog.grab_set() 
        dialog.focus_set()
        
        dialog_width = 350
        dialog_height = 250
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width // 2) - (dialog_width // 2)
        y = (screen_height // 2) - (dialog_height // 2)
        dialog.geometry(f'{dialog_width}x{dialog_height}+{x}+{y}')
        
        dialog_frame = ttk.Frame(dialog, padding=15)
        dialog_frame.pack(fill='both', expand=True)
        dialog_frame.columnconfigure(1, weight=1)
        
        fields = ['Name', 'Author', 'Publication Date']
        entries = {}
        
        for i, field in enumerate(fields):
            ttk.Label(dialog_frame, text=f"{field}:").grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(dialog_frame, width=30)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky='ew')
            entries[field] = entry
            
            if not is_create and media_data:
                 # Publication Date in backend is publication_date
                 key = 'publication_date' if field == 'Publication Date' else field.lower() 
                 entry.insert(0, media_data.get(key, '')) 


        ttk.Label(dialog_frame, text="Category:").grid(row=len(fields), column=0, padx=5, pady=5, sticky='w')
        category_var = tk.StringVar(dialog_frame)
        category_options = self.categories[1:]
        category_menu = ttk.Combobox(dialog_frame, textvariable=category_var, values=category_options, state="readonly", width=28)
        category_menu.grid(row=len(fields), column=1, padx=5, pady=5, sticky="ew")

        if not is_create and media_data:
            category_var.set(media_data.get('category'))
        else:
            category_var.set(category_options[0]) 

        def submit_crud():
            payload = {
                'name': entries['Name'].get().strip(),
                'author': entries['Author'].get().strip(),
                'publication_date': entries['Publication Date'].get().strip(),
                'category': category_var.get()
            }
            
            if not all(payload.values()):
                messagebox.showerror("Validation Error", "All fields must be filled.")
                return
            
            # Simple YYYY-MM-DD format validation
            try:
                datetime.strptime(payload['publication_date'], '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Validation Error", "Publication Date must be in YYYY-MM-DD format (e.g., 2024-01-15).")
                return

            if is_create:
                success, _ = self._post_put_delete_favorite(f"{BASE_URL}/media", method='POST', json_data=payload)
                message = "New media item created successfully!"
            else:
                success, _ = self._post_put_delete_favorite(f"{BASE_URL}/media/{media_data['id']}", method='PUT', json_data=payload)
                message = f"Media ID {media_data['id']} updated successfully!"
                
            if success:
                messagebox.showinfo("Success", message)
                dialog.destroy()
                self.load_all_media() 
            # Error message handled in _post_put_delete_favorite

        button_frame = ttk.Frame(dialog_frame)
        button_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10, sticky='e')
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save" if not is_create else "Create", command=submit_crud, style='Edit.TButton' if not is_create else 'Accent.TButton').pack(side=tk.LEFT, padx=5)

        dialog.wait_window(dialog) 

    def delete_media(self):
        media_id = self.current_selected_id
        media_name = self.detail_labels['Name'].cget("text")

        if not media_id or not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete '{media_name}' (ID: {media_id})?"):
            return

        success, _ = self._post_put_delete_favorite(f"{BASE_URL}/media/{media_id}", method='DELETE')
            
        if success:
            messagebox.showinfo("Success", f"Media item '{media_name}' deleted.")
            self.load_all_media() 
            self.clear_metadata_display()

    # --- Screenshot Management Methods ---
    def upload_screenshot(self):
        """Upload a screenshot for the selected media item."""
        media_id = self.current_selected_id
        if not media_id:
            messagebox.showwarning("No Selection", "Please select a media item first.")
            return
        
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select a Screenshot",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All Files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{BASE_URL}/media/{media_id}/screenshot", files=files)
                
            response.raise_for_status()
            messagebox.showinfo("Success", "Screenshot uploaded successfully!")
            # Refresh the display
            self.display_metadata_from_tree(None)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to upload screenshot: {str(e)}")

    def delete_screenshot(self):
        """Delete the screenshot for the selected media item."""
        media_id = self.current_selected_id
        if not media_id:
            messagebox.showwarning("No Selection", "Please select a media item first.")
            return
        
        if not messagebox.askyesno("Confirm", "Delete the screenshot for this media item?"):
            return
        
        try:
            response = requests.delete(f"{BASE_URL}/media/{media_id}/screenshot")
            response.raise_for_status()
            messagebox.showinfo("Success", "Screenshot deleted successfully!")
            # Refresh the display
            self.display_metadata_from_tree(None)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to delete screenshot: {str(e)}")

    def view_screenshot(self):
        """View the screenshot for the selected media item in a new window."""
        media_id = self.current_selected_id
        if not media_id:
            messagebox.showwarning("No Selection", "Please select a media item first.")
            return
        
        try:
            # Get screenshot info
            response = requests.get(f"{BASE_URL}/media/{media_id}/screenshot")
            response.raise_for_status()
            data = response.json()
            
            if not data.get('has_screenshot'):
                messagebox.showinfo("No Screenshot", "This media item has no screenshot yet.")
                return
            
            screenshot_path = data.get('screenshot_path')
            if not screenshot_path:
                return
            
            # Download and display the image
            img_response = requests.get(f"{BASE_URL}/{screenshot_path}")
            img_response.raise_for_status()
            
            # Create image from bytes
            img = Image.open(io.BytesIO(img_response.content))
            
            # Create new window to display image
            img_window = tk.Toplevel(self.master)
            img_window.title(f"Screenshot - {self.detail_labels['Name'].cget('text')}")
            
            # Resize image to fit window (max 600x600)
            img.thumbnail((600, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            label = ttk.Label(img_window, image=photo)
            label.image = photo
            label.pack(padx=10, pady=10)
            
            # Save button
            def save_image():
                save_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All Files", "*.*")]
                )
                if save_path:
                    img.save(save_path)
                    messagebox.showinfo("Success", f"Image saved to {save_path}")
            
            ttk.Button(img_window, text="💾 Save Image", command=save_image).pack(pady=10)
            
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Failed to view screenshot: {str(e)}")

if __name__ == '__main__':
    root = tk.Tk()
    app = LibraryDeskApp(root)
    root.mainloop()