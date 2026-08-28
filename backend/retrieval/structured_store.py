import sqlite3
import os

# Ensure the database is stored in the data/ directory at the root of the project
DB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'inventory.db')
)

def get_connection():
    """Helper function to get a database connection."""
    return sqlite3.connect(DB_PATH)

def init_inventory_db():
    """Initializes the SQLite database and creates the units table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS units (
            unit_id TEXT PRIMARY KEY,
            tower TEXT NOT NULL,
            floor INTEGER NOT NULL,
            bhk INTEGER NOT NULL,
            area_sqft INTEGER NOT NULL,
            price_inr REAL NOT NULL,
            possession_date TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def seed_sample_units():
    """Seeds the database with realistic sample units if it's empty."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM units")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    sample_units = [
        ('A-101', 'Tower A', 1, 2, 1200, 15000000, '2026-12-01', 'Available'),
        ('A-201', 'Tower A', 2, 2, 1200, 15500000, '2026-12-01', 'Sold'),
        ('A-502', 'Tower A', 5, 3, 1800, 25000000, '2026-12-01', 'Available'),
        ('A-1001', 'Tower A', 10, 4, 2500, 38000000, '2026-12-01', 'Available'),
        ('B-101', 'Tower B', 1, 2, 1150, 14500000, '2027-06-01', 'Available'),
        ('B-302', 'Tower B', 3, 3, 1750, 24000000, '2027-06-01', 'Available'),
        ('B-701', 'Tower B', 7, 2, 1150, 15200000, '2027-06-01', 'Available'),
        ('B-1202', 'Tower B', 12, 4, 2600, 40000000, '2027-06-01', 'Hold'),
    ]
    
    cursor.executemany('''
        INSERT INTO units (unit_id, tower, floor, bhk, area_sqft, price_inr, possession_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_units)
    
    conn.commit()
    conn.close()

def query_units(bhk=None, max_price=None, tower=None):
    """
    Queries the unit inventory. 
    Always filters for status='Available'.
    """
    conn = get_connection()
    # Return as dict for easier usage
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM units WHERE status = 'Available'"
    params = []
    
    if bhk is not None:
        query += " AND bhk = ?"
        params.append(bhk)
        
    if max_price is not None:
        query += " AND price_inr <= ?"
        params.append(max_price)
        
    if tower is not None:
        query += " AND tower = ?"
        params.append(tower)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    conn.close()
    
    return [dict(row) for row in rows]


if __name__ == "__main__":
    init_inventory_db()
    seed_sample_units()
    units = query_units()
    print(f"Initialized and seeded database. Available units count: {len(units)}")
    for u in units:
        print(u)

