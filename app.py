from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from flask_bcrypt import Bcrypt
import requests
import secrets
import os
from dotenv import load_dotenv
from decimal import Decimal
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))
bcrypt = Bcrypt(app)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "karthik@213"),
    "database": os.getenv("DB_NAME", "cafe_x"),
    "pool_name": "mypool",
    "pool_size": 5,
    "autocommit": True
}

# Initialize connection pool
db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)

def get_db_connection():
    try:
        connection = db_pool.get_connection()
        cursor = connection.cursor(dictionary=True)
        return connection, cursor
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        raise

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("signin"))
        return f(*args, **kwargs)
    return decorated_function

def handle_db_error(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return jsonify({"success": False, "error": "Database error occurred"}), 500
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
    return decorated_function

TOKEN_RATE = 10  # 1 Token = 10 INR


def get_crypto_price(crypto, currency="inr"):
    """ Fetch real-time crypto price """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies={currency}"
    response = requests.get(url).json()
    return response.get(crypto, {}).get(currency, None)

@app.route("/")
def home():
    user_id = session.get("user_id")
    username, tokens = None, 0

    if user_id:
        cursor.execute("SELECT name, tokens FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:
            username, tokens = user
            session["username"] = username  

    return render_template("index.html", username=username, tokens=tokens)

@app.route("/token_page")
def token_page():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    user_id = session["user_id"]
    cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
    tokens = cursor.fetchone()[0] or 0  # ✅ Ensure default value if NULL

    return render_template("token.html", tokens=tokens)  # ✅ Pass tokens to template



@app.route("/get_token_balance", methods=["GET"])
def get_token_balance():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    user_id = session["user_id"]
    db, cursor = get_db_connection()  # ✅ Correctly unpack db and cursor

    cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    
    cursor.close()
    db.close()

    tokens = float(result[0]) if result and result[0] is not None else 0
    return jsonify({"success": True, "tokens": tokens})



from decimal import Decimal

@app.route("/process_payment", methods=["POST"])
def process_payment():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    amount_inr = float(data["amount_inr"])  # ✅ Convert INR input to float
    tokens_to_add = Decimal(amount_inr / TOKEN_RATE)  # ✅ Convert INR to Tokens

    user_id = session["user_id"]

    # ✅ Fetch current token balance and ensure it's a Decimal
    cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
    current_tokens = cursor.fetchone()[0] or Decimal(0)
    current_tokens = Decimal(current_tokens)  # ✅ Ensure it's a Decimal

    new_balance = current_tokens + tokens_to_add  # ✅ Safe addition

    # ✅ Update the database with new token balance
    cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, user_id))
    db.commit()

    return jsonify({
        "success": True,
        "tokens_added": float(tokens_to_add),
        "new_balance": float(new_balance),  
        "redirect_url": url_for('token_page')  # ✅ Redirect to Token Page
    })

@app.route("/deduct_tokens", methods=["POST"])
def deduct_tokens():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    cart_price = float(data.get("cart_price"))
    user_id = session["user_id"]

    cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
    current_tokens = cursor.fetchone()[0]

    if current_tokens < cart_price:
        return jsonify({"success": False, "error": "Insufficient tokens"}), 400

    new_balance = current_tokens - cart_price
    cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, user_id))
    db.commit()

    return jsonify({"success": True, "remaining_tokens": new_balance})

from decimal import Decimal  # ✅ Import Decimal for proper calculations

@app.route("/get_cart_total", methods=["GET"])
def get_cart_total():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    user_id = session["user_id"]
    cursor.execute("SELECT SUM(total_price) FROM cart WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    total_price = float(result[0]) if result and result[0] is not None else 0
    return jsonify({"success": True, "total_price": total_price})



from decimal import Decimal
@app.route("/pay_with_tokens", methods=["POST"])
def pay_with_tokens():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    total_price = float(data["total_price"])
    user_id = session["user_id"]

    # ✅ Get user's current token balance
    cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()

    if result is None:
        return jsonify({"success": False, "error": "User not found"}), 400

    current_tokens = float(result[0])

    if current_tokens < total_price:
        return jsonify({"success": False, "error": "Not enough tokens to complete purchase"}), 400

    # ✅ Deduct tokens
    new_balance = current_tokens - total_price
    cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, user_id))

    # ✅ Save order to `orders` table
    cursor.execute("INSERT INTO orders (user_id, total_price, purchase_time) VALUES (%s, %s, NOW())",
                   (user_id, total_price))

    # ✅ Clear user's cart after successful purchase
    cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
    
    db.commit()

    return jsonify({
        "success": True,
        "remaining_tokens": new_balance
    })



@app.route("/confirm_payment")
def confirm_payment():
    return redirect(url_for("home"))



# ✅ Serve Sign-In Page
@app.route("/signin")
def signin_page():
    return render_template("signin.html")

# ✅ Serve Sign-Up Page
@app.route("/signup")
def signup_page():
    return render_template("signup.html")

# ✅ Sign-Up API (Fixing Duplicate Route)
@app.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.form
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not all([name, email, password]):
            return jsonify({"success": False, "error": "All fields are required"}), 400

        # Validate email format
        if not "@" in email or not "." in email:
            return jsonify({"success": False, "error": "Invalid email format"}), 400

        # Validate password strength
        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters long"}), 400

        connection, cursor = get_db_connection()
        try:
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"success": False, "error": "Email already exists"}), 400

            # Hash password and create user
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
            cursor.execute("""
                INSERT INTO users (name, email, password_hash) 
                VALUES (%s, %s, %s)
            """, (name, email, hashed_password))
            connection.commit()

            # Get user ID and create session
            user_id = cursor.lastrowid
            session["user_id"] = user_id
            session["username"] = name

            return jsonify({
                "success": True,
                "message": "Account created successfully",
                "redirect_url": url_for("home")
            })
        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        print(f"Signup error: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred during signup"}), 500

@app.route("/signin", methods=["POST"])
def signin():
    try:
        if request.content_type == "application/json":
            data = request.json
        else:
            data = request.form

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400

        connection, cursor = get_db_connection()
        try:
            cursor.execute("""
                SELECT id, name, password_hash 
                FROM users 
                WHERE email = %s
            """, (email,))
            user = cursor.fetchone()

            if not user:
                return jsonify({"success": False, "error": "Invalid email or password"}), 401

            if bcrypt.check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["name"]
                return jsonify({
                    "success": True,
                    "message": "Login successful",
                    "redirect_url": url_for("home")
                })
            else:
                return jsonify({"success": False, "error": "Invalid email or password"}), 401

        finally:
            cursor.close()
            connection.close()

    except Exception as e:
        print(f"Signin error: {str(e)}")
        return jsonify({"success": False, "error": "An error occurred during signin"}), 500

# ✅ Check if user is logged in
@app.route("/is_logged_in")
def is_logged_in():
    user_id = session.get("user_id")
    username = session.get("username")
    return jsonify({
        "logged_in": user_id is not None,
        "username": username
    })

# ✅ Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return jsonify({
        "success": True,
        "message": "Logged out successfully",
        "redirect_url": url_for("home")
    })


@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    user_id = session["user_id"]

    # ✅ Fetch user details
    cursor.execute("SELECT name, email, tokens FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    user_data = {"name": user[0], "email": user[1], "tokens": user[2]}

    # ✅ Fetch order history
    cursor.execute("SELECT total_price, purchase_time FROM orders WHERE user_id = %s", (user_id,))
    orders = cursor.fetchall()

    return render_template("profile.html", user=user_data, orders=orders)


# ✅ Serve Menu Page
@app.route("/menu")
def menu():
    connection, cursor = get_db_connection()
    try:
        cursor.execute("""
            SELECT id, name, price, description, image_url, rating 
            FROM menu 
            ORDER BY name
        """)
        menu_items = cursor.fetchall()
        return render_template("menu.html", menu_items=menu_items)
    except Exception as e:
        print(f"Menu error: {str(e)}")
        return render_template("menu.html", menu_items=[], error="Error loading menu")
    finally:
        cursor.close()
        connection.close()

@app.route("/get_menu_prices")
def get_menu_prices():
    connection, cursor = get_db_connection()
    try:
        cursor.execute("SELECT name, price FROM menu")
        menu_items = cursor.fetchall()
        menu_prices = {item["name"]: float(item["price"]) for item in menu_items}
        return jsonify(menu_prices)
    except Exception as e:
        print(f"Menu prices error: {str(e)}")
        return jsonify({"success": False, "error": "Error loading menu prices"}), 500
    finally:
        cursor.close()
        connection.close()


@app.route("/cart")
@login_required
def cart():
    connection, cursor = get_db_connection()
    try:
        user_id = session["user_id"]
        cursor.execute("""
            SELECT c.id, m.name as item_name, c.quantity, m.price, c.total_price 
            FROM cart c
            JOIN menu m ON c.item_id = m.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()
        
        total_price = sum(item["total_price"] for item in cart_items)
        
        return render_template("cart.html", 
                             cart_items=cart_items, 
                             total_price=float(total_price))
    except Exception as e:
        print(f"Cart error: {str(e)}")
        return jsonify({"success": False, "error": "Error loading cart"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route("/add_to_cart", methods=["POST"])
@login_required
@handle_db_error
def add_to_cart():
    data = request.json
    user_id = session["user_id"]
    item_name = data.get("item_name")
    quantity = int(data.get("quantity", 1))

    connection, cursor = get_db_connection()
    try:
        # Get item price from menu
        cursor.execute("SELECT id, price FROM menu WHERE name = %s", (item_name,))
        menu_item = cursor.fetchone()
        if not menu_item:
            return jsonify({"success": False, "error": "Item not found in menu"}), 404

        item_id, price = menu_item["id"], float(menu_item["price"])
        total_price = price * quantity

        # Check if item already exists in cart
        cursor.execute("""
            SELECT quantity, total_price 
            FROM cart 
            WHERE user_id = %s AND item_id = %s
        """, (user_id, item_id))
        existing_item = cursor.fetchone()

        if existing_item:
            # Update existing item
            new_quantity = existing_item["quantity"] + quantity
            new_total_price = price * new_quantity
            cursor.execute("""
                UPDATE cart 
                SET quantity = %s, total_price = %s 
                WHERE user_id = %s AND item_id = %s
            """, (new_quantity, new_total_price, user_id, item_id))
        else:
            # Add new item
            cursor.execute("""
                INSERT INTO cart (user_id, item_id, quantity, total_price)
                VALUES (%s, %s, %s, %s)
            """, (user_id, item_id, quantity, total_price))

        connection.commit()
        return jsonify({"success": True, "message": "Item added to cart!"})
    finally:
        cursor.close()
        connection.close()

@app.route('/get_cart/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    cart_data = [
        {"id": item.id, "item_name": item.item_name, "price": item.price, 
         "quantity": item.quantity, "total_price": item.total_price}
        for item in cart_items
    ]
    return jsonify({"success": True, "cart": cart_data})
@app.route('/update_cart', methods=['POST'])
def update_cart():
    data = request.json
    item_id = data['item_id']
    new_quantity = data['quantity']

    item = Cart.query.get(item_id)
    if item:
        item.quantity = new_quantity
        item.total_price = item.price * new_quantity
        db.session.commit()
        return jsonify({"success": True, "message": "Cart updated!"})
    
    return jsonify({"success": False, "error": "Item not found!"})
@app.route('/remove_item/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    item = Cart.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True, "message": "Item removed from cart!"})
    
    return jsonify({"success": False, "error": "Item not found!"})
@app.route('/clear_cart/<int:user_id>', methods=['POST'])
def clear_cart(user_id):
    Cart.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"success": True, "message": "Cart cleared after checkout!"})



@app.route("/update_cart_quantity", methods=["POST"])
def update_cart_quantity():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    user_id = session["user_id"]
    item_name = data["item"]
    new_quantity = int(data["quantity"])

    if new_quantity <= 0:
        cursor.execute("DELETE FROM cart WHERE user_id = %s AND item_name = %s", (user_id, item_name))
    else:
        # ✅ Fetch price from menu
        cursor.execute("SELECT price FROM menu WHERE name = %s", (item_name,))
        menu_item = cursor.fetchone()
        if not menu_item:
            return jsonify({"success": False, "error": "Item not found in menu"}), 400

        price = float(menu_item[0])
        new_total_price = new_quantity * price  # ✅ Update total price

        cursor.execute("UPDATE cart SET quantity = %s, total_price = %s WHERE user_id = %s AND item_name = %s", 
                       (new_quantity, new_total_price, user_id, item_name))

    db.commit()
    return jsonify({"success": True})



# ✅ Get Cart Count API
@app.route("/cart_count")
def cart_count():
    if "user_id" not in session:
        return jsonify({"count": 0})  

    user_id = session["user_id"]
    cursor.execute("SELECT SUM(quantity) FROM cart WHERE user_id = %s", (user_id,))
    count = cursor.fetchone()[0] or 0  
    return jsonify({"count": count})

@app.route('/get_cart_data', methods=['POST'])
def get_cart_data():
    data = request.json
    cart = data.get("cart", [])

    if not cart:
        return jsonify({"success": False, "cart": [], "total_price": 0.00})

    conn = get_db_connection()
    cursor = conn.cursor()

    total_price = 0
    cart_items = []

    for item in cart:
        menu_id = item["menu_id"]
        quantity = item["quantity"]

        cursor.execute("SELECT item_name, price FROM menu WHERE id = ?", (menu_id,))
        menu_item = cursor.fetchone()

        if menu_item:
            item_name = menu_item["item_name"]
            price = float(menu_item["price"])
            total_price += price * quantity

            cart_items.append({
                "menu_id": menu_id,
                "name": item_name,
                "price": price,
                "quantity": quantity
            })

    conn.close()

    return jsonify({"success": True, "cart": cart_items, "total_price": total_price})


def get_crypto_price(crypto, currency="inr"):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto}&vs_currencies={currency}"
    response = requests.get(url).json()
    return response.get(crypto, {}).get(currency, None)

# ✅ Payment Page Route
@app.route("/payment")
def payment():
    return render_template("payment.html")

# ✅ Process Payment



# ✅ Check Payment Status (Simulation)
@app.route("/payment_status/<transaction_id>")
def payment_status(transaction_id):
    cursor.execute("SELECT * FROM payments WHERE transaction_id = %s", (transaction_id,))
    payment = cursor.fetchone()
    
    if not payment:
        return jsonify({"success": False, "error": "Transaction not found"}), 404
    
    return jsonify({"success": True, "status": "Pending", "transaction_id": transaction_id})


if __name__ == "__main__":
    app.run(debug=True)
