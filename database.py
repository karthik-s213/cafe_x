import mysql.connector
from mysql.connector import Error

try:
    # Connect to MySQL Server (without specifying database initially)
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="karthik@213"
    )
    cursor = db.cursor()

    # Create the database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS cafe_x")
    print("✅ Database created successfully!")

    # Close the initial connection
    cursor.close()
    db.close()

    # Reconnect to the newly created database
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="karthik@213",
        database="cafe_x"
    )
    cursor = db.cursor()

    # Create Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        tokens DECIMAL(10,2) DEFAULT 0.00,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✅ Users table created successfully!")

    # Drop and recreate the table if it exists with wrong schema
    try:
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("""
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            tokens DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("✅ Users table recreated successfully!")
    except Error as e:
        print(f"❌ Error recreating users table: {e}")

    # Create Menu Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        description TEXT,
        image_url VARCHAR(255)
    )
    """)
    print("✅ Menu table created successfully!")

    # Create Cart Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cart (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        item_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        price DECIMAL(10,2) NOT NULL,
        total_price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES menu(id) ON DELETE CASCADE
    )
    """)
    print("✅ Cart table created successfully!")

    # Create Orders Table
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

    # Create Order Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_id INT NOT NULL,
        item_id INT NOT NULL,
        quantity INT NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        total_price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES menu(id) ON DELETE CASCADE
    )
    """)
    print("✅ Order items table created successfully!")

    # Insert Menu Items (Check if menu is empty before inserting)
    cursor.execute("SELECT COUNT(*) FROM menu")
    menu_count = cursor.fetchone()[0]

    if menu_count == 0:
        menu_items = [
            ('Burger', 20.00, 'Delicious beef burger with fresh vegetables', 'https://images6.alphacoders.com/870/thumb-1920-870777.jpg'),
            ('Pizza', 20.00, 'Classic pepperoni pizza with melted cheese', 'https://c4.wallpaperflare.com/wallpaper/1005/1000/931/delicious-pizza-pepperoni-pizza-wallpaper-preview.jpg'),
            ('Sandwich', 15.00, 'Fresh sandwich with your choice of filling', 'https://images2.alphacoders.com/129/1294747.jpg'),
            ('Tacos', 18.00, 'Mexican style tacos with spicy sauce', 'https://img.freepik.com/free-photo/mexican-tacos-with-beef-tomato-sauce-salsa_2829-14218.jpg'),
            ('Chocolate Coffee', 10.00, 'Rich chocolate coffee with whipped cream', 'https://images6.alphacoders.com/940/thumb-1920-940750.jpg'),
            ('Cold Coffee', 12.00, 'Refreshing cold coffee with ice cream', 'https://img.freepik.com/free-photo/vertical-closeup-plastic-cup-cold-coffee-with-vanilla-cream_181624-57827.jpg'),
            ('Espresso', 10.00, 'Strong and pure espresso shot', 'https://images8.alphacoders.com/134/1341444.png'),
            ('Cappuccino', 14.00, 'Classic cappuccino with frothy milk', 'https://i.pinimg.com/736x/e0/14/f7/e014f7b059759f7525b183ef6549d2f2.jpg'),
            ('Sprite', 8.00, 'Refreshing lemon-lime soda', 'https://mir-s3-cdn-cf.behance.net/projects/404/25f402135347067.Y3JvcCwzNDAyLDI2NjAsMCwxMDk.jpg'),
            ('Pepsi', 7.00, 'Classic cola drink', 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQnFAHjU2tvyNL65vBpnFwWKGDQ_6MeNnT_1Q&s'),
            ('Fanta', 6.00, 'Orange flavored soda', 'https://t3.ftcdn.net/jpg/02/94/38/74/360_F_294387467_RvmDw6qbKMYVO6CPZlqCaKCDghl8VT0m.jpg'),
            ('Coca Cola', 5.00, 'World\'s favorite cola', 'https://cdn.uengage.io/uploads/5/image-259575-1716368916.jpeg')
        ]
        
        cursor.executemany(
            "INSERT INTO menu (name, price, description, image_url) VALUES (%s, %s, %s, %s)",
            menu_items
        )
        db.commit()
        print("✅ Menu items inserted successfully!")
    else:
        print("✅ Menu items already exist. Skipping insertion.")

    # Commit all changes
    db.commit()
    print("✅ All database operations completed successfully!")

except Error as e:
    print(f"❌ Error: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'db' in locals():
        db.close()
        print("✅ Database connection closed.")
