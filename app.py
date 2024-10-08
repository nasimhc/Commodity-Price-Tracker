import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import hashlib
import os

# Initialize database
conn = sqlite3.connect('price_tracker.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS products
             (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
c.execute('''CREATE TABLE IF NOT EXISTS importers
             (id INTEGER PRIMARY KEY, name TEXT UNIQUE)''')
c.execute('''CREATE TABLE IF NOT EXISTS prices
             (id INTEGER PRIMARY KEY, date TEXT, product_id INTEGER, importer_id INTEGER, price REAL,
             FOREIGN KEY (product_id) REFERENCES products(id),
             FOREIGN KEY (importer_id) REFERENCES importers(id))''')
conn.commit()

# Function to hash the password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Set the correct password hash here
password = os.getenv("PASSWORD")
CORRECT_PASSWORD_HASH = hash_password(password)

# Function to check the password
def check_password():
    def password_entered():
        if hash_password(st.session_state["password"]) == CORRECT_PASSWORD_HASH:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Enter the password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Enter the password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

# Only show the main app if the password is correct
if check_password():
    # Your existing app code goes here
    def add_product(name):
        c.execute("INSERT OR IGNORE INTO products (name) VALUES (?)", (name,))
        conn.commit()

    def add_importer(name):
        c.execute("INSERT OR IGNORE INTO importers (name) VALUES (?)", (name,))
        conn.commit()

    def get_products():
        c.execute("SELECT name FROM products")
        return [row[0] for row in c.fetchall()]

    def get_importers():
        c.execute("SELECT name FROM importers")
        return [row[0] for row in c.fetchall()]

    def add_price(date, product, importer, price):
        c.execute("SELECT id FROM products WHERE name=?", (product,))
        product_id = c.fetchone()[0]
        c.execute("SELECT id FROM importers WHERE name=?", (importer,))
        importer_id = c.fetchone()[0]
        c.execute("INSERT INTO prices (date, product_id, importer_id, price) VALUES (?, ?, ?, ?)",
                  (date, product_id, importer_id, price))
        conn.commit()

    def get_price_history(product, importer):
        query = '''
        SELECT prices.date, prices.price
        FROM prices
        JOIN products ON prices.product_id = products.id
        JOIN importers ON prices.importer_id = importers.id
        WHERE products.name = ? AND importers.name = ?
        ORDER BY prices.date
        '''
        df = pd.read_sql_query(query, conn, params=(product, importer))
        df['date'] = pd.to_datetime(df['date'])
        return df

    st.title("Product Price Tracker")

    # Sidebar for adding products and importers
    with st.sidebar:
        st.header("Add New Product")
        new_product = st.text_input("Product Name")
        if st.button("Add Product"):
            add_product(new_product)
            st.success(f"Added product: {new_product}")

        st.header("Add New Importer")
        new_importer = st.text_input("Importer Name")
        if st.button("Add Importer"):
            add_importer(new_importer)
            st.success(f"Added importer: {new_importer}")

    # Main area for price entry and visualization
    st.header("Record New Price")
    col1, col2, col3 = st.columns(3)

    with col1:
        date = st.date_input("Date")
    with col2:
        product = st.selectbox("Product", get_products())
    with col3:
        importer = st.selectbox("Importer", get_importers())

    price = st.number_input("Price", min_value=0.0, format="%.2f")

    if st.button("Record Price"):
        add_price(date.strftime("%Y-%m-%d"), product, importer, price)
        st.success("Price recorded successfully!")

    # Price history visualization
    st.header("Price History")
    viz_product = st.selectbox("Select Product", get_products(), key="viz_product")
    viz_importer = st.selectbox("Select Importer", get_importers(), key="viz_importer")

    if st.button("Show Price History"):
        df = get_price_history(viz_product, viz_importer)
        if not df.empty:
            fig = px.line(df, x='date', y='price', title=f"Price History for {viz_product} ({viz_importer})")
            st.plotly_chart(fig)
        else:
            st.info("No price history available for the selected product and importer.")

# Close the database connection when the app is done
conn.close()