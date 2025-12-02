"""
Simple Tkinter GUI to run predefined MySQL queries against tv_shows_db

Usage: python tv_query_gui_simple.py

Edit DB_PASSWORD below, then run. Select a query, fill in any parameters, and click Run.

Requires: pymysql, tkinter (built-in)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import pymysql


# ===== DATABASE CREDENTIALS =====
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = 'dataPassword'  # <-- Enter your MySQL password here
DB_NAME = 'tv_shows_db'
# ================================


# ===== PREDEFINED QUERIES =====
QUERIES = {
    'Top 20 Shows': {
        'sql': """
            SELECT id, name, first_air_date, popularity
            FROM shows
            ORDER BY popularity DESC
            LIMIT 20
        """,
        'params': []
    },
    'Search by Name': {
        'sql': """
            SELECT id, name, overview, popularity
            FROM shows
            WHERE name LIKE CONCAT('%%', %s, '%%')
        """,
        'params': ['search_term']
    },
    'Shows by Genre': {
        'sql': """
            SELECT s.id, s.name, s.first_air_date, s.popularity, s.vote_average, s.vote_count
            FROM shows s
            JOIN show_genres sg ON s.id = sg.show_id
            JOIN genres g ON sg.genre_id = g.genre_id
            WHERE g.name = %s
            ORDER BY s.popularity DESC
        """,
        'params': ['genre_name']
    },
    'Genres for Show': {
        'sql': """
            SELECT s.id AS show_id, s.name AS show_name, g.genre_id, g.name AS genre_name
            FROM shows s
            JOIN show_genres sg ON s.id = sg.show_id
            JOIN genres g ON sg.genre_id = g.genre_id
            WHERE s.id = %s
        """,
        'params': ['show_id']
    },
    'Count by Genre': {
        'sql': """
            SELECT g.genre_id, g.name, COUNT(sg.show_id) AS show_count
            FROM genres g
            LEFT JOIN show_genres sg ON g.genre_id = sg.genre_id
            GROUP BY g.genre_id, g.name
            ORDER BY show_count DESC
        """,
        'params': []
    }
}
# ==============================


class TVQueryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TV Shows Query Tool")
        self.root.geometry('900x600')
        
        self.connection = None
        self.param_entries = []
        
        # Query selection
        query_frame = ttk.LabelFrame(root, text='Select Query')
        query_frame.pack(fill='x', padx=10, pady=10)
        
        self.query_var = tk.StringVar()
        query_dropdown = ttk.Combobox(query_frame, textvariable=self.query_var, 
                                      values=list(QUERIES.keys()), state='readonly', width=40)
        query_dropdown.pack(padx=10, pady=10)
        query_dropdown.bind('<<ComboboxSelected>>', self.on_query_select)
        
        # Parameters
        self.param_frame = ttk.LabelFrame(root, text='Parameters')
        self.param_frame.pack(fill='x', padx=10, pady=10)
        
        # Run button
        run_button = ttk.Button(root, text='Run Query', command=self.run_query)
        run_button.pack(pady=10)
        
        # Insert button
        insert_button = ttk.Button(root, text='Insert New Show', command=self.open_insert_window)
        insert_button.pack(pady=5)
        
        # Results
        result_frame = ttk.LabelFrame(root, text='Results')
        result_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(result_frame, show='headings')
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Status
        self.status = tk.StringVar(value='Ready')
        status_bar = ttk.Label(root, textvariable=self.status, relief='sunken', anchor='w')
        status_bar.pack(fill='x', side='bottom')
        
        # Connect to database
        self.connect_db()
    
    def connect_db(self):
        try:
            self.connection = pymysql.connect(
                host=DB_HOST, port=DB_PORT, user=DB_USER, 
                password=DB_PASSWORD, database=DB_NAME,
                charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor
            )
            self.status.set(f'Connected to {DB_NAME}')
        except Exception as e:
            messagebox.showerror('Connection Error', str(e))
            self.status.set('Connection failed')
    
    def on_query_select(self, event=None):
        # Clear parameter inputs
        for widget in self.param_frame.winfo_children():
            widget.destroy()
        self.param_entries = []
        
        query_name = self.query_var.get()
        params = QUERIES[query_name]['params']
        
        if params:
            for i, param_name in enumerate(params):
                ttk.Label(self.param_frame, text=f'{param_name}:').grid(
                    row=0, column=i*2, padx=5, pady=10, sticky='e')
                entry = ttk.Entry(self.param_frame, width=20)
                entry.grid(row=0, column=i*2+1, padx=5, pady=10, sticky='w')
                self.param_entries.append(entry)
    
    def run_query(self):
        if not self.connection:
            messagebox.showwarning('Not Connected', 'No database connection')
            return
        
        query_name = self.query_var.get()
        if not query_name:
            messagebox.showwarning('No Query', 'Please select a query')
            return
        
        query_info = QUERIES[query_name]
        sql = query_info['sql']
        
        # Get parameter values
        params = [entry.get() for entry in self.param_entries]
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params if params else None)
                results = cursor.fetchall()
            
            self.display_results(results)
            self.status.set(f'{query_name}: {len(results)} row(s) returned')
        
        except Exception as e:
            messagebox.showerror('Query Error', str(e))
            self.status.set('Query failed')
    
    def display_results(self, results):
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        
        if not results:
            self.tree['columns'] = ()
            return
        
        # Setup columns
        columns = list(results[0].keys())
        self.tree['columns'] = columns
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        
        # Insert data
        for row in results:
            values = [row[col] for col in columns]
            self.tree.insert('', 'end', values=values)
    
    def open_insert_window(self):
        """Open a new window for inserting a show into the database."""
        insert_window = tk.Toplevel(self.root)
        insert_window.title("Insert New Show")
        insert_window.geometry('550x700')
        
        # Create scrollable frame
        canvas = tk.Canvas(insert_window)
        scrollbar = ttk.Scrollbar(insert_window, orient='vertical', command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create input fields
        ttk.Label(scrollable_frame, text="Enter Show Information", font=('Arial', 12, 'bold')).pack(pady=10)
        
        form_frame = ttk.Frame(scrollable_frame)
        form_frame.pack(padx=20, pady=10, fill='both', expand=True)
        
        # Fields dictionary to store entries
        fields = {}
        
        # Define fields
        field_defs = [
            ('id', 'Show ID (integer)'),
            ('name', 'Show Name'),
            ('original_name', 'Original Name'),
            ('overview', 'Overview (description)'),
            ('first_air_date', 'First Air Date (YYYY-MM-DD)'),
            ('popularity', 'Popularity (decimal)'),
            ('vote_average', 'Vote Average (0-10)'),
            ('vote_count', 'Vote Count (integer)'),
            ('genres', 'Genre IDs (comma-separated, e.g., 18,80)'),
            ('countries', 'Country Codes (comma-separated, e.g., US,GB)')
        ]
        
        row = 0
        for field_name, label_text in field_defs:
            ttk.Label(form_frame, text=label_text + ':').grid(row=row, column=0, sticky='w', pady=5, padx=5)
            entry = ttk.Entry(form_frame, width=40)
            entry.grid(row=row, column=1, pady=5, padx=5)
            fields[field_name] = entry
            row += 1
        
        # Submit button
        def submit_insert():
            try:
                # Get basic show values
                show_id = int(fields['id'].get())
                name = fields['name'].get()
                original_name = fields['original_name'].get()
                overview = fields['overview'].get()
                first_air_date = fields['first_air_date'].get() if fields['first_air_date'].get() else None
                popularity = float(fields['popularity'].get()) if fields['popularity'].get() else None
                vote_average = float(fields['vote_average'].get()) if fields['vote_average'].get() else None
                vote_count = int(fields['vote_count'].get()) if fields['vote_count'].get() else None
                
                # Get genres and countries
                genres_input = fields['genres'].get().strip()
                countries_input = fields['countries'].get().strip()
                
                genre_ids = [int(g.strip()) for g in genres_input.split(',') if g.strip()] if genres_input else []
                country_codes = [c.strip().upper() for c in countries_input.split(',') if c.strip()] if countries_input else []
                
                # Begin transaction - disable autocommit to ensure all-or-nothing insert
                self.connection.begin()
                
                try:
                    with self.connection.cursor() as cursor:
                        # Insert into shows table (main table)
                        insert_show_sql = """
                            INSERT INTO shows (id, name, original_name, overview, first_air_date, 
                                              popularity, vote_average, vote_count)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(insert_show_sql, (show_id, name, original_name, overview, 
                                                         first_air_date, popularity, vote_average, vote_count))
                        
                        # Insert genres into show_genres table (many-to-many relationship)
                        for genre_id in genre_ids:
                            # First ensure genre exists in genres table
                            cursor.execute("INSERT IGNORE INTO genres (genre_id) VALUES (%s)", (genre_id,))
                            # Then link show to genre
                            cursor.execute("INSERT INTO show_genres (show_id, genre_id) VALUES (%s, %s)", 
                                          (show_id, genre_id))
                        
                        # Insert countries into show_countries table (many-to-many relationship)
                        for country_code in country_codes:
                            # First ensure country exists in countries table
                            cursor.execute("INSERT IGNORE INTO countries (country_code) VALUES (%s)", (country_code,))
                            # Then link show to country
                            cursor.execute("INSERT INTO show_countries (show_id, country_code) VALUES (%s, %s)", 
                                          (show_id, country_code))
                        
                        # Insert into popularity_history table (tracks popularity metrics)
                        if popularity is not None or vote_average is not None or vote_count is not None:
                            cursor.execute("""
                                INSERT INTO popularity_history (show_id, popularity, vote_average, vote_count)
                                VALUES (%s, %s, %s, %s)
                            """, (show_id, popularity, vote_average, vote_count))
                    
                    # Commit transaction - all inserts succeeded
                    self.connection.commit()
                    messagebox.showinfo('Success', f'Show "{name}" inserted successfully with {len(genre_ids)} genre(s) and {len(country_codes)} country/countries!')
                    insert_window.destroy()
                    
                except Exception as db_error:
                    # Rollback transaction - undo all changes if any insert failed
                    self.connection.rollback()
                    raise db_error
                
            except ValueError as e:
                messagebox.showerror('Input Error', f'Invalid input format: {e}')
            except Exception as e:
                messagebox.showerror('Database Error', f'Failed to insert show: {e}')
        
        submit_btn = ttk.Button(scrollable_frame, text='Insert Show', command=submit_insert)
        submit_btn.pack(pady=20)
        
        cancel_btn = ttk.Button(scrollable_frame, text='Cancel', command=insert_window.destroy)
        cancel_btn.pack(pady=5)
        
        # Pack canvas and scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')


if __name__ == '__main__':
    root = tk.Tk()
    app = TVQueryGUI(root)
    root.mainloop()

