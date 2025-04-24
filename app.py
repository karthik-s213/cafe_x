from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import mysql.connector
from flask_bcrypt import Bcrypt
import requests
import secrets
import os
from dotenv import load_dotenv
from decimal import Decimal
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from mysql.connector.cursor import MySQLCursorDict
from decimal import Decimal  # ✅ Import Decimal for proper calculations
import time
import razorpay
# Then in get_db_connection():
# Load environment variables
load_dotenv()
import secrets

# Generate a 32-byte secret key (hex format)
secret_key = secrets.token_hex(32)
app = Flask(__name__)
app.secret_key =  secret_key
bcrypt = Bcrypt(app)

# Configure session
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "cafe-x-db-q1v6.onrender.com"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "karthik@213"),
    "database": os.getenv("DB_NAME", "cafe_x"),
    "pool_name": "mypool",
    "pool_size": 5,
    "autocommit": True,
    "use_pure": True,
    
}

# Initialize connection pool
# db_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)

# def get_db_connection():
#     max_retries = 3
#     retry_count = 0
    
#     while retry_count < max_retries:
#         try:
#             connection = db_pool.get_connection()
#             cursor = connection.cursor(cursor_class=MySQLCursorDict)
#             return connection, cursor
#         except mysql.connector.Error as err:
#             retry_count += 1
#             print(f"Database connection attempt {retry_count} failed: {err}")
#             if retry_count == max_retries:
#                 raise
#             time.sleep(1)  # Wait before retrying


# ─── place these near the top, right after DB_CONFIG ──────────────────────────
_pool = None           # global holder
_POOL_RETRIES = 5
_POOL_DELAY   = 3      # seconds


def init_db_pool() -> None:
    """Create the MySQL connection‑pool once, with retries."""
    global _pool
    if _pool:                         # already done
        return

    import mysql.connector
    from mysql.connector import pooling

    last_error = None
    for i in range(_POOL_RETRIES):
        try:
            _pool = pooling.MySQLConnectionPool(**DB_CONFIG)
            print("✅ MySQL pool initialised")
            return
        except mysql.connector.Error as err:
            last_error = err
            print(f"⏳ MySQL not ready ({err}); retry {i+1}/{_POOL_RETRIES}")
            time.sleep(_POOL_DELAY)
    raise RuntimeError(f"Could not connect to MySQL: {last_error}")


def get_db_connection():
    """Return (connection, cursor) – call init_db_pool() if needed."""
    if _pool is None:
        init_db_pool()                         # ❶ create on first real use
    conn = _pool.get_connection()
    cursor = conn.cursor(cursor_class=MySQLCursorDict)
    return conn, cursor


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"Session Data: {session}")
        if "user_id" not in session:
            flash("Please sign in to access this page", "error")
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
    if "user_id" in session:
        connection, cursor = get_db_connection()
        try:
            # Get user info
            cursor.execute("SELECT name, email, tokens FROM users WHERE id = %s", (session["user_id"],))
            user = cursor.fetchone()
            
            # Get recent orders
            cursor.execute("""
                SELECT o.id, o.total_price, o.purchase_time,
                       oi.item_id, oi.quantity, oi.price, oi.total_price as item_total,
                       m.name as item_name
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN menu m ON oi.item_id = m.id
                WHERE o.user_id = %s
                ORDER BY o.purchase_time DESC
                LIMIT 5
            """, (session["user_id"],))
            recent_orders = cursor.fetchall()
            
            # Format recent orders
            formatted_orders = []
            for order in recent_orders:
                
                formatted_orders.append({
                    'order_id': order['id'],
                    'date': order['purchase_time'].strftime('%Y-%m-%d %H:%M:%S') if order.get('purchase_time') else '',
                    'item_name': order['item_name'],
                    'quantity': order['quantity'],
                    'price': float(order['price']),
                    'total_price': float(order['item_total'])
                })
            
            return render_template("index.html", 
                                username=user["name"],
                                email=user["email"],
                                tokens=float(user["tokens"]) if user["tokens"] else 0.00,
                                recent_orders=formatted_orders)
        finally:
            cursor.close()
            connection.close()
    return render_template("index.html", username=None, email=None, tokens=0.00, recent_orders=[])

@app.route("/get_token_balance", methods=["GET"])
def get_token_balance():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    user_id = session["user_id"]
    connection, cursor = get_db_connection()

    try:
        cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        tokens = float(result["tokens"]) if result and result["tokens"] is not None else 0
        return jsonify({"success": True, "tokens": tokens})
    finally:
        cursor.close()
        connection.close()

from decimal import Decimal

@app.route("/process_payment", methods=["POST"])
@login_required
def process_payment():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    amount_inr = float(data["amount_inr"])
    tokens_to_add = amount_inr   # Convert INR to Tokens

    connection, cursor = get_db_connection()
    try:
        # Get current token balance
        cursor.execute("SELECT tokens FROM users WHERE id = %s", (session["user_id"],))
        current_tokens = float(cursor.fetchone()["tokens"] or 0)
        
        # Add new tokens
        new_balance = current_tokens + tokens_to_add
        cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, session["user_id"]))
        
        connection.commit()
        
        return jsonify({
            "success": True,
            "tokens_added": tokens_to_add,
            "new_balance": new_balance,
            "redirect_url": url_for('cart')  # Redirect back to cart
        })
        
    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        connection.rollback()
        return jsonify({
            "success": False,
            "error": "An error occurred while processing your payment"
        }), 500
    finally:
        cursor.close()
        connection.close()

@app.route("/deduct_tokens", methods=["POST"])
def deduct_tokens():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    cart_price = float(data.get("cart_price"))
    user_id = session["user_id"]

    connection, cursor = get_db_connection()  # Added connection handling
    try:
        cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        current_tokens = float(result["tokens"])  # Using dict access

        if current_tokens < cart_price:
            return jsonify({"success": False, "error": "Insufficient tokens"}), 400

        new_balance = current_tokens - cart_price
        cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, user_id))
        connection.commit()  # Added commit

        return jsonify({"success": True, "remaining_tokens": new_balance})
    finally:
        cursor.close()
        connection.close()

@app.route("/get_cart_total", methods=["GET"])
def get_cart_total():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    connection, cursor = get_db_connection()
    try:
        user_id = session["user_id"]
        cursor.execute("SELECT SUM(total_price) FROM cart WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        total_price = float(result[0]) if result and result[0] is not None else 0
        return jsonify({"success": True, "total_price": total_price})
    finally:
        cursor.close()
        connection.close()

@app.route("/pay_with_tokens", methods=["POST"])
def pay_with_tokens():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    data = request.json
    total_price = float(data["total_price"])
    user_id = session["user_id"]

    connection, cursor = get_db_connection()
    try:
        # Get user's current token balance
        cursor.execute("SELECT tokens FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if result is None:
            return jsonify({"success": False, "error": "User not found"}), 400

        current_tokens = float(result["tokens"])  # Using dict access

        if current_tokens < total_price:
            return jsonify({"success": False, "error": "Not enough tokens to complete purchase"}), 400

        # Deduct tokens
        new_balance = current_tokens - total_price
        cursor.execute("UPDATE users SET tokens = %s WHERE id = %s", (new_balance, user_id))

        # Save order
        cursor.execute("""
            INSERT INTO orders (user_id, total_price, purchase_time) 
            VALUES (%s, %s, NOW())
        """, (user_id, total_price))
        
        connection.commit()  # Added commit
        return jsonify({"success": True, "remaining_tokens": new_balance})
    finally:
        cursor.close()
        connection.close()

@app.route("/confirm_payment")
def confirm_payment():
    return redirect(url_for("home"))

# ✅ Serve Sign-In Page
@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        next_page = request.args.get("next")

        connection, cursor = get_db_connection()
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and bcrypt.check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["user_tokens"] = float(user["tokens"]) if user["tokens"] else 0.00
                session.permanent = True
                
                if next_page:
                    return redirect(next_page)
                else:
                    return redirect(url_for("home"))
            else:
                if not user:
                    flash("Account not found. Please sign up first.", "error")
                else:
                    flash("Invalid password. Please try again.", "error")
                return redirect(url_for("signin"))
        except Exception as e:
            print(f"Signin error: {str(e)}")
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for("signin"))
        finally:
            cursor.close()
            connection.close()
    
    return render_template("signin.html")

@app.route("/signout")
def signout():
    session.clear()
    return redirect(url_for("home"))

# ✅ Serve Sign-Up Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not all([name, email, password]):
            flash("All fields are required", "error")
            return redirect(url_for("signup"))
        
        connection, cursor = get_db_connection()
        try:
            # Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("Email already registered", "error")
                return redirect(url_for("signup"))
            
            # Hash the password
            hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
            
            # Insert new user
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            connection.commit()
            
            # Get the new user's ID
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            user_id = cursor.fetchone()["id"]
            
            # Set session data
            session["user_id"] = user_id
            session["user_name"] = name
            session["user_email"] = email
            session["user_tokens"] = 0.00
            session.permanent = True
            
            flash("Account created successfully!", "success")
            return redirect(url_for("home"))
            
        except Exception as e:
            print(f"Signup error: {str(e)}")
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for("signup"))
        finally:
            cursor.close()
            connection.close()
    
    return render_template("signup.html")

# ✅ Check if user is logged in
@app.route("/is_logged_in")
def is_logged_in():
    return jsonify({"logged_in": "user_id" in session})

# ✅ Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/profile")
@login_required
def profile():
    connection, cursor = get_db_connection()
    try:
        # Get user details
        cursor.execute("SELECT name, email, tokens FROM users WHERE id = %s", (session["user_id"],))
        user = cursor.fetchone()
        
        if not user:
            flash("User not found", "error")
            return redirect(url_for("home"))
        
        # Get user's orders
        cursor.execute("""
            SELECT o.id, o.total_price, o.purchase_time,
                   oi.item_id, oi.quantity, oi.price, oi.total_price as item_total,
                   m.name as item_name
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN menu m ON oi.item_id = m.id
            WHERE o.user_id = %s
            ORDER BY o.purchase_time DESC
        """, (session["user_id"],))
        orders = cursor.fetchall()
        
        # Format orders for display
        formatted_orders = []
        for order in orders:
            try:
                formatted_orders.append({
                    'id': order['id'],
                    'total_price': float(order['total_price']),
                    'purchase_time': order['purchase_time'].strftime('%Y-%m-%d %H:%M:%S') if order['purchase_time'] else '',
                    'product': [{
                        'name': order['item_name'],
                        'quantity': order['quantity'],
                        'total_price': float(order['item_total'])
                    }]
                })
            except Exception as e:
                print(f"Error formatting order: {str(e)}")
                continue
        
        return render_template("profile.html", 
                             user=user,
                             orders=formatted_orders)
                             
    except Exception as e:
        print(f"Profile error: {str(e)}")
        flash("An error occurred while loading your profile.", "error")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        connection.close()

# ✅ Serve Menu Page
@app.route("/menu")
@login_required
def menu():
    connection, cursor = get_db_connection()
    try:
        cursor.execute("SELECT * FROM menu")
        menu_items = cursor.fetchall()
        return render_template("menu.html", menu_items=menu_items)
    finally:
        cursor.close()
        connection.close()

@app.route("/add_to_cart/<int:item_id>", methods=["POST"])
@login_required
def add_to_cart(item_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please sign in to add items to cart"})
    
    user_id = session["user_id"]
    connection, cursor = get_db_connection()
    
    try:
        # Get item details
        cursor.execute("SELECT price FROM menu WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"success": False, "message": "Item not found"})
        
        # Check if item already in cart
        cursor.execute("""
            SELECT quantity, total_price 
            FROM cart 
            WHERE user_id = %s AND item_id = %s
        """, (user_id, item_id))
        existing_item = cursor.fetchone()
        
        if existing_item:
            # Update quantity and total price
            new_quantity = existing_item["quantity"] + 1
            new_total = new_quantity * item["price"]
            cursor.execute("""
                UPDATE cart 
                SET quantity = %s, total_price = %s 
                WHERE user_id = %s AND item_id = %s
            """, (new_quantity, new_total, user_id, item_id))
        else:
            # Add new item to cart
            cursor.execute("""
                INSERT INTO cart (user_id, item_id, quantity, price, total_price)
                VALUES (%s, %s, 1, %s, %s)
            """, (user_id, item_id, item["price"], item["price"]))
        
        connection.commit()
        
        # Get updated cart count
        cursor.execute("SELECT SUM(quantity) as total FROM cart WHERE user_id = %s", (user_id,))
        cart_count = cursor.fetchone()["total"] or 0
        
        return jsonify({
            "success": True,
            "message": "Item added to cart",
            "cart_count": cart_count
        })
        
    except Exception as e:
        print(f"Add to cart error: {str(e)}")
        return jsonify({"success": False, "message": "Error adding item to cart"})
    finally:
        cursor.close()
        connection.close()

@app.route("/cart")
@login_required
def cart():
    user_id = session.get("user_id")
    connection, cursor = get_db_connection()
    
    try:
        # Get cart items with menu details
        cursor.execute("""
            SELECT c.id, c.quantity, c.price, c.total_price,
                   m.name, m.image_url
            FROM cart c
            JOIN menu m ON c.item_id = m.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cursor.fetchall()
        
        # Calculate total
        total = sum(float(item["total_price"]) for item in cart_items)
        
        return render_template("cart.html", cart_items=cart_items, total=total)
        
    except Exception as e:
        print(f"Cart error: {str(e)}")
        flash("Error loading cart", "error")
        return redirect(url_for("menu"))
    finally:
        cursor.close()
        connection.close()

@app.route("/update_cart_count")
@login_required
def update_cart_count():
    user_id = session.get("user_id")
    connection, cursor = get_db_connection()
    
    try:
        cursor.execute("SELECT SUM(quantity) as total FROM cart WHERE user_id = %s", (user_id,))
        cart_count = cursor.fetchone()["total"] or 0
        return jsonify({"cart_count": cart_count})
    finally:
        cursor.close()
        connection.close()

@app.route("/update_cart_quantity", methods=["POST"])
def update_cart_quantity():
    if "user_id" not in session:
        return jsonify({"success": False, "error": "User not logged in"}), 401

    connection, cursor = get_db_connection()
    try:
        data = request.json
        user_id = session["user_id"]
        item_name = data.get("item_name")
        new_quantity = int(data.get("quantity", 1))

        if new_quantity <= 0:
            cursor.execute("DELETE FROM cart WHERE user_id = %s AND item_name = %s", 
                         (user_id, item_name))
        else:
            cursor.execute("SELECT price FROM menu WHERE name = %s", (item_name,))
            result = cursor.fetchone()
            if not result:
                return jsonify({"success": False, "error": "Item not found"}), 404

            price = float(result["price"])
            new_total_price = price * new_quantity

            cursor.execute("""
                UPDATE cart 
                SET quantity = %s, total_price = %s 
                WHERE user_id = %s AND item_name = %s
            """, (new_quantity, new_total_price, user_id, item_name))

        connection.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Update cart error: {str(e)}")
        return jsonify({"success": False, "error": "Error updating cart"}), 500
    finally:
        cursor.close()
        connection.close()

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data['message'].lower()

    # Simple reply logic
    if "menu" in user_message:
        reply = "You can view the menu by clicking on the Menu tab!"
    elif "token" in user_message:
        reply = "Your token balance is shown on the Token page."
    elif "hello" in user_message:
        reply = "Hi there! How can I help you today?"
    else:
        reply = "I'm not sure how to help with that yet."

    return jsonify({"reply": reply})

@app.route("/update_cart/<int:item_id>/<int:change>")
@login_required
def update_cart(item_id, change):
    if "user_id" not in session:
        return jsonify({
            "success": False, 
            "message": "Please sign in to update cart",
            "status": "unauthorized"
        }), 401
    
    user_id = session["user_id"]
    connection, cursor = None, None
    
    try:
        connection, cursor = get_db_connection()
        
        # 1. Verify item exists and get current data
        cursor.execute("""
            SELECT c.quantity, m.price, m.name
            FROM cart c
            JOIN menu m ON c.item_id = m.id
            WHERE c.user_id = %s AND c.item_id = %s
        """, (user_id, item_id))
        cart_item = cursor.fetchone()
        
        if not cart_item:
            return jsonify({
                "success": False,
                "message": "Item not found in cart",
                "status": "not_found"
            }), 404
        
        # 2. Calculate new values
        current_qty = cart_item["quantity"]
        new_qty = current_qty + change
        
        # 3. Handle quantity changes
        if new_qty <= 0:
            # Remove item completely
            cursor.execute("""
                DELETE FROM cart 
                WHERE user_id = %s AND item_id = %s
            """, (user_id, item_id))
            item_removed = True
        else:
            # Update quantity
            new_total = round(new_qty * float(cart_item["price"]), 2)
            cursor.execute("""
                UPDATE cart 
                SET quantity = %s, 
                    total_price = %s
                WHERE user_id = %s AND item_id = %s
            """, (new_qty, new_total, user_id, item_id))
            item_removed = False
        
        # 4. Get updated cart summary
        cursor.execute("""
            SELECT 
                SUM(quantity) as total_items,
                SUM(total_price) as grand_total
            FROM cart 
            WHERE user_id = %s
        """, (user_id,))
        cart_summary = cursor.fetchone()
        
        connection.commit()
        
        # 5. Prepare response
        response = {
            "success": True,
            "item_id": item_id,
            "item_removed": item_removed,
            "cart_total": float(cart_summary["grand_total"] or 0),
            "total_items": cart_summary["total_items"] or 0
        }
        
        if not item_removed:
            response.update({
                "new_quantity": new_qty,
                "new_total": float(new_total),
                "item_name": cart_item["name"]
            })
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Cart update error: {str(e)}")
        if connection:
            connection.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating cart",
            "error": str(e),
            "status": "error"
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
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
        print(f"Get menu prices error: {str(e)}")
        return jsonify({})
    finally:
        cursor.close()
        connection.close()

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

# ✅ Payment Page Route
# @app.route("/payment")
# def payment():
#     return render_template("payment.html")

# ✅ Process Payment

# ✅ Check Payment Status (Simulation)
@app.route("/payment_status/<transaction_id>")
def payment_status(transaction_id):
    cursor.execute("SELECT * FROM payments WHERE transaction_id = %s", (transaction_id,))
    payment = cursor.fetchone()
    
    if not payment:
        return jsonify({"success": False, "error": "Transaction not found"}), 404
    
    return jsonify({"success": True, "status": "Pending", "transaction_id": transaction_id})

@app.route('/checkout')
@login_required
def checkout():
    connection, cursor = get_db_connection()
    try:
        # Get cart items and calculate total
        cursor.execute('''
            SELECT c.id, c.quantity, c.item_id, m.price, m.name, m.image_url
            FROM cart c
            JOIN menu m ON c.item_id = m.id
            WHERE c.user_id = %s
        ''', (session['user_id'],))
        cart_items = cursor.fetchall()
        
        if not cart_items:
            return jsonify({'success': False, 'message': 'Your cart is empty!'})
            
        # Get user's current tokens
        cursor.execute('SELECT tokens FROM users WHERE id = %s', (session['user_id'],))
        user_result = cursor.fetchone()
        user_tokens = float(user_result['tokens'])
        
        cart_total = sum(float(item['quantity'] * item['price']) for item in cart_items)
        
        if user_tokens < cart_total:
            return jsonify({
                'success': False, 
                'message': 'Insufficient tokens! Please add more tokens to your account.',
                'redirect': url_for('payment')
            })
            
        try:
            # Create order first
            cursor.execute('''
                INSERT INTO orders (user_id, total_price, purchase_time)
                VALUES (%s, %s, NOW())
            ''', (session['user_id'], cart_total))
            order_id = cursor.lastrowid
            
            # Add order items
            for item in cart_items:
                item_total = float(item['quantity'] * item['price'])
                cursor.execute('''
                    INSERT INTO order_items (order_id, item_id, quantity, price, total_price)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (order_id, item['item_id'], item['quantity'], item['price'], item_total))
            
            # Update user's tokens
            new_tokens = user_tokens - cart_total
            cursor.execute('UPDATE users SET tokens = %s WHERE id = %s', 
                         (new_tokens, session['user_id']))
            
            # Clear cart
            cursor.execute('DELETE FROM cart WHERE user_id = %s', (session['user_id'],))
            
            # Commit the transaction
            connection.commit()
            
            return jsonify({
                'success': True,
                'message': 'Order placed successfully! Thank you for your purchase.'
            })
            
        except Exception as e:
            print(f"Error in checkout: {str(e)}")
            connection.rollback()
            return jsonify({
                'success': False,
                'message': 'An error occurred while processing your order.'
            })
            
    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your order.'
        })
    finally:
        cursor.close()
        connection.close()

@app.route("/add_tokens", methods=["POST"])
@login_required
def add_tokens():
    amount = float(request.form.get("amount", 0))
    if amount != 1000:
        flash("Invalid amount. Please enter 1000 to get 100 tokens.", "error")
        return redirect(url_for("payment"))
    
    connection, cursor = get_db_connection()
    try:
        # Get current tokens
        cursor.execute("SELECT tokens FROM users WHERE id = %s", (session["user_id"],))
        current_tokens = float(cursor.fetchone()["tokens"] or 0)
        
        # Add 100 tokens
        new_tokens = current_tokens + 100
        cursor.execute("""
            UPDATE users 
            SET tokens = %s 
            WHERE id = %s
        """, (new_tokens, session["user_id"]))
        
        connection.commit()
        flash("100 tokens added successfully!", "success")
        return redirect(url_for("cart"))
    finally:
        cursor.close()
        connection.close()




import razorpay
client = razorpay.Client(auth=("rzp_test_nlqM4lzusperIk", "03U0PAPLKvolfY9FUOEvYWWk"))
@app.route('/payment')
@login_required
def payment():
    return render_template('form.html')

@app.route('/pay', methods=["GET", "POST"])
def pay():
    if request.method == "POST":
        try:
            amount = int(request.form.get("amt", 0))
            if amount <= 0:
                flash("Please enter a valid amount", "error")
                return redirect(url_for("payment"))
                
            amount_in_paise = amount * 100
            data = {
                "amount": amount_in_paise,
                "currency": "INR",
                "receipt": f"order_rcptid_{secrets.token_hex(4)}"
            }
            payment = client.order.create(data=data)
            
            return render_template(
                "payment.html",
                pdata=[amount, payment["id"]]
            )
        except Exception as e:
            print(f"Payment creation error: {str(e)}")
            flash("Error creating payment. Please try again.", "error")
            return redirect(url_for("payment"))
            
    return redirect(url_for("payment"))

@app.route('/success', methods=["POST"])
def success():
    try:
        pid = request.form.get("razorpay_payment_id")
        ordid = request.form.get("razorpay_order_id")
        sign = request.form.get("razorpay_signature")
        
        params = {
            'razorpay_order_id': ordid,
            'razorpay_payment_id': pid,
            'razorpay_signature': sign
        }
        
        if client.utility.verify_payment_signature(params):
            # Get payment details to know amount
            payment = client.payment.fetch(pid)
            amount_paid = float(payment['amount']) / 100  # Convert from paise to rupees
            
            # Calculate tokens to add (1 token = 10 INR)
            tokens_to_add = amount_paid / TOKEN_RATE
            
            # Update user tokens
            connection, cursor = get_db_connection()
            try:
                cursor.execute(
                    "SELECT tokens FROM users WHERE id = %s",
                    (session["user_id"],)
                )
                current_tokens = float(cursor.fetchone()["tokens"] or 0)
                new_balance = current_tokens + tokens_to_add
                
                cursor.execute(
                    "UPDATE users SET tokens = %s WHERE id = %s",
                    (new_balance, session["user_id"])
                )
                connection.commit()
                
                flash(f"Payment successful! {tokens_to_add} tokens added to your account.", "success")
                return redirect(url_for("profile"))
            finally:
                cursor.close()
                connection.close()
        
        flash("Payment verification failed", "error")
        return redirect(url_for("payment"))
        
    except Exception as e:
        print(f"Payment processing error: {str(e)}")
        flash("Error processing payment. Please contact support.", "error")
        return redirect(url_for("payment"))

# Add a global error handler
@app.errorhandler(Exception)
def handle_error(e):
    print(f"Application error: {str(e)}")
    return jsonify({
        "success": False,
        "error": "An unexpected error occurred",
        "details": str(e) if app.debug else None
    }), 500

@app.errorhandler(401)
def unauthorized(e):
    flash("Please sign in to access this page", "error")
    return redirect(url_for('signin'))

@app.errorhandler(404)
def page_not_found(e):
    flash("Page not found", "error")
    return redirect(url_for('home'))


if __name__ == "__main__":
    app.run(debug=True)
