import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "karthik@213"),
    "database": os.getenv("DB_NAME", "cafe_x")
}

# Connect to MySQL Server (without specifying database initially)
db = mysql.connector.connect(
    host=DB_CONFIG["host"],
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"]
)

cursor = db.cursor()

# Create the database if it doesn't exist
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
print("✅ Database created successfully!")

# Reconnect to the newly created database
db = mysql.connector.connect(**DB_CONFIG)
cursor = db.cursor()

# Create Users Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    tokens DECIMAL(10,2) DEFAULT 0
)
""")

# Create Menu Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS menu (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    rating DECIMAL(2,1) DEFAULT 0.0
)
""")

# Create Cart Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS cart (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    total_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES menu(id) ON DELETE CASCADE
)
""")

print("✅ Tables created successfully!")

# Insert Menu Items (Check if menu is empty before inserting)
cursor.execute("SELECT COUNT(*) FROM menu")
menu_count = cursor.fetchone()[0]

if menu_count == 0:
    menu_items = [
        ('Burger', 100.00, 'Delicious beef burger with fresh vegetables', 'https://images6.alphacoders.com/870/thumb-1920-870777.jpg', 4.5),
        ('Pizza', 120.00, 'Classic Italian pizza with your favorite toppings', 'https://c4.wallpaperflare.com/wallpaper/1005/1000/931/delicious-pizza-pepperoni-pizza-wallpaper-preview.jpg', 4.5),
        ('Sandwich', 150.00, 'Fresh sandwich with premium ingredients', 'https://images2.alphacoders.com/129/1294747.jpg', 4.0),
        ('Tacos', 180.00, 'Authentic Mexican tacos with spicy sauce', 'https://img.freepik.com/free-photo/mexican-tacos-with-beef-tomato-sauce-salsa_2829-14218.jpg', 4.0),
        ('Chocolate Coffee', 100.00, 'Rich chocolate coffee with whipped cream', 'https://images6.alphacoders.com/940/thumb-1920-940750.jpg', 4.0),
        ('Cold Coffee', 120.00, 'Refreshing cold coffee with ice cream', 'https://img.freepik.com/free-photo/vertical-closeup-plastic-cup-cold-coffee-with-vanilla-cream_181624-57827.jpg', 4.0),
        ('Espresso', 100.00, 'Strong and pure espresso shot', 'https://images8.alphacoders.com/134/1341444.png', 3.5),
        ('Cappuccino', 140.00, 'Classic cappuccino with perfect foam', 'https://i.pinimg.com/736x/e0/14/f7/e014f7b059759f7525b183ef6549d2f2.jpg', 4.0),
        ('Sprite', 80.00, 'Refreshing lemon-lime soda', 'https://mir-s3-cdn-cf.behance.net/projects/404/25f402135347067.Y3JvcCwzNDAyLDI2NjAsMCwxMDk.jpg', 3.5),
        ('Pepsi', 70.00, 'Classic cola drink', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQnFAHjU2tvyNL65vBpnFwWKGDQ_6MeNnT_1Q&s', 3.5),
        ('Fanta', 60.00, 'Orange flavored soda', 'https://t3.ftcdn.net/jpg/02/94/38/74/360_F_294387467_RvmDw6qbKMYVO6CPZlqCaKCDghl8VT0m.jpg', 3.5),
        ('Coca Cola', 50.00, 'World\'s favorite cola drink', 'https://cdn.uengage.io/uploads/5/image-259575-1716368916.jpeg', 4.0)
    ]
    
    cursor.executemany(
        "INSERT INTO menu (name, price, description, image_url, rating) VALUES (%s, %s, %s, %s, %s)",
        menu_items
    )
    db.commit()
    print("✅ Menu items inserted successfully!")
else:
    print("✅ Menu items already exist. Skipping insertion.")

# Create Orders Table (Stores past purchases)
cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    purchase_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
""")

print("✅ Orders table created successfully!")

# Close the connection
cursor.close()
db.close()
