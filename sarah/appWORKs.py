from flask import Flask, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True, origins="*")
app.secret_key = 'supersecretkey123!'

# Database config
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7MDAHfa6mah()',
    'database': 'user_system'
}

def get_db():
    return mysql.connector.connect(**db_config)

# 🔁 Auto-update drivers
def update_driver_availability(conn):
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE DeliveryPersonnel dp
            SET dp.status = 'Available'
            WHERE NOT EXISTS (
                SELECT 1 FROM Orders o
                WHERE o.delivery_person_id = dp.delivery_id AND o.delivery_status = 'Pending'
            )
        """)
        conn.commit()
        cursor.close()
    except Error as e:
        print("Driver update error:", str(e))


# 🔐 Register
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, address, phone, email, password, role)
            VALUES (%s, %s, %s, %s, %s, 'user')
        """, (data['name'], data['address'], data['phone'], data['email'], data['password']))
        conn.commit()
        return jsonify({'message': '✅ Registered successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🔐 Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    if email == 'admin@a.a' and password == '123':
        session.clear()
        session['admin'] = True
        return jsonify({'message': '✅ Admin login successful', 'role': 'admin'}), 200

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            session.clear()
            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']
            session['user_id'] = user['customer_id']
            if user['role'] == 'restaurant_admin':
                session['restaurant_id'] = user.get('restaurant_id')
            return jsonify({
                'message': '✅ Login successful',
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'restaurant_id': user.get('restaurant_id')
            }), 200
        else:
            return jsonify({'error': '❌ Invalid email or password'}), 401
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🚪 Logout
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

# 🧠 Session Info
@app.route('/session-user', methods=['GET'])
def session_user():
    if session.get('admin'):
        return jsonify({'email': 'admin@a.a', 'name': 'Admin', 'role': 'admin'}), 200
    elif 'email' in session:
        response = {
            'email': session['email'],
            'name': session['name'],
            'role': session['role']
        }
        if session['role'] == 'restaurant_admin':
            response['restaurant_id'] = session.get('restaurant_id')
        return jsonify(response), 200
    else:
        return jsonify({'error': 'No user logged in'}), 401

# 📋 Get Restaurants
@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Restaurants")
        return jsonify({'restaurants': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 📄 Get Menus
@app.route('/menus/<int:restaurant_id>', methods=['GET'])
def get_menu(restaurant_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Menus WHERE restaurant_id = %s AND availability = 'In Stock'", (restaurant_id,))
        return jsonify({'menu': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🛒 Place Order
@app.route('/place-order', methods=['POST'])
def place_order():
    if 'email' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items provided'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT customer_id, name FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        customer_id = user['customer_id']
        customer_name = user['name']
        total = sum(float(item['price']) for item in items)

        cursor.execute("""
            SELECT * FROM DeliveryPersonnel
            WHERE status = 'Available'
            ORDER BY assigned_orders ASC
            LIMIT 1
        """)
        delivery = cursor.fetchone()
        if not delivery:
            return jsonify({'error': 'No delivery personnel available'}), 503

        cursor.execute("""
            INSERT INTO Orders (customer_id, order_date, total_amount, delivery_status, delivery_time, payment_status, delivery_person_id)
            VALUES (%s, NOW(), %s, 'Pending', NULL, 'Paid', %s)
        """, (customer_id, total, delivery['delivery_id']))
        conn.commit()
        order_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                INSERT INTO Order_Items (order_id, menu_id, quantity, item_price)
                VALUES (%s, %s, 1, %s)
            """, (order_id, item['menu_id'], item['price']))

        cursor.execute("""
            UPDATE DeliveryPersonnel
            SET assigned_orders = assigned_orders + 1, status = 'Assigned'
            WHERE delivery_id = %s
        """, (delivery['delivery_id'],))
        conn.commit()

        update_driver_availability(conn)

        return jsonify({
            'message': '✅ Order placed successfully',
            'order_id': order_id,
            'customer_name': customer_name,
            'delivery_person': delivery['name'],
            'total': total,
            'status': 'Preparing your order',
            'estimated_time': '30 minutes',
            'items': items
        }), 200

    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🚚 Get User Orders
@app.route('/user/orders', methods=['GET'])
def get_user_orders():
    if 'email' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT customer_id FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        cursor.execute("""
            SELECT o.order_id, o.order_date, o.delivery_status, o.total_amount,
                   d.name AS delivery_person
            FROM Orders o
            LEFT JOIN DeliveryPersonnel d ON o.delivery_person_id = d.delivery_id
            WHERE o.customer_id = %s
            ORDER BY o.order_date DESC
        """, (user['customer_id'],))
        return jsonify({'orders': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ✅ Add Delivery Personnel
@app.route('/admin/add-delivery-personnel', methods=['POST'])
def add_delivery_personnel():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    name = data.get('name')
    phone = data.get('phone')

    if not name or not phone:
        return jsonify({'error': 'Name and phone are required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO DeliveryPersonnel (name, phone) VALUES (%s, %s)", (name, phone))
        conn.commit()
        return jsonify({'message': '✅ Delivery personnel added'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ❌ Delete Delivery Personnel
@app.route('/admin/delete-delivery-personnel', methods=['POST'])
def delete_delivery_personnel():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    phone = data.get('phone')
    if not phone:
        return jsonify({'error': 'Phone number required'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM DeliveryPersonnel WHERE phone = %s", (phone,))
        conn.commit()
        return jsonify({'message': '✅ Delivery personnel deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
@app.route('/restaurant/orders', methods=['GET'])
def get_restaurant_orders():
    if 'role' not in session or session['role'] != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403

    restaurant_id = session.get('restaurant_id')
    if not restaurant_id:
        return jsonify({'error': 'Restaurant ID not found in session'}), 400

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT o.order_id, o.order_date, o.delivery_status, o.total_amount,
                   u.name AS customer_name, d.name AS delivery_person
            FROM Orders o
            JOIN users u ON o.customer_id = u.customer_id
            LEFT JOIN DeliveryPersonnel d ON o.delivery_person_id = d.delivery_id
            JOIN Order_Items oi ON o.order_id = oi.order_id
            JOIN Menus m ON oi.menu_id = m.menu_id
            WHERE m.restaurant_id = %s
            GROUP BY o.order_id
            ORDER BY o.order_date DESC
        """, (restaurant_id,))
        orders = cursor.fetchall()

        return jsonify({'orders': orders}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ❌ Cancel Order
@app.route('/cancel-order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401

        cursor.execute("SELECT * FROM Orders WHERE order_id = %s AND customer_id = %s", (order_id, session['user_id']))
        order = cursor.fetchone()
        if not order:
            return jsonify({'error': 'Unauthorized'}), 403

        cursor.execute("UPDATE Orders SET delivery_status = 'Cancelled' WHERE order_id = %s", (order_id,))
        conn.commit()
        update_driver_availability(conn)
        return jsonify({'message': '✅ Order cancelled'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🔄 Admin: Refresh driver status
@app.route('/reset-drivers', methods=['POST'])
def reset_drivers():
    try:
        conn = get_db()
        update_driver_availability(conn)
        conn.close()
        return jsonify({'message': '✅ Drivers refreshed'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
@app.route('/restaurant/mark-ready/<int:order_id>', methods=['POST'])
def mark_order_ready(order_id):
    if 'role' not in session or session['role'] != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE Orders SET delivery_status = 'On Delivery' WHERE order_id = %s", (order_id,))
        conn.commit()
        return jsonify({'message': '✅ Order marked as On Delivery'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


# ▶️ Run
if __name__ == '__main__':
    app.run(debug=True)
