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

# 🔐 Register
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, address, phone, email, password, role)
            VALUES (%s, %s, %s, %s, %s, 'user')
        """, (data['name'], data['address'], data['phone'], data['email'], data['password']))
        conn.commit()
        return jsonify({'message': '✅ Registered successfully'}), 200
    except Error as e:
        if 'Duplicate' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
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
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            session.clear()
            session['email'] = user['email']
            session['name'] = user['name']
            session['role'] = user['role']
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

# 🚪 Logout
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

# ✏️ Update Profile
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'email' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.get_json()
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET name=%s, address=%s, phone=%s WHERE email=%s
        """, (data['name'], data['address'], data['phone'], session['email']))
        conn.commit()
        session['name'] = data['name']
        return jsonify({'message': '✅ Profile updated'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🧍 Get user profile
@app.route('/get-user', methods=['GET'])
def get_user():
    if 'email' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, address, phone, email FROM users WHERE email = %s", (session['email'],))
        user = cursor.fetchone()
        return jsonify({'user': user}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ✅ Assign restaurant admin
@app.route('/admin/assign-restaurant-admin', methods=['POST'])
def assign_restaurant_admin():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    email = data.get('email')
    restaurant_id = data.get('restaurant_id')

    if not email or not restaurant_id:
        return jsonify({'error': 'Email and restaurant ID required'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET role = 'restaurant_admin', restaurant_id = %s
            WHERE email = %s
        """, (restaurant_id, email))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': '✅ User promoted to restaurant admin'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🏢 Admin: Add Restaurant
@app.route('/admin/add-restaurant', methods=['POST'])
def add_restaurant():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Restaurants (name, address, contact_number, cuisine_type)
            VALUES (%s, %s, %s, %s)
        """, (data['name'], data['address'], data['contact_number'], data['cuisine_type']))
        conn.commit()
        return jsonify({'message': '✅ Restaurant added'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ✏️ Admin: Update Restaurant
@app.route('/admin/update-restaurant', methods=['POST'])
def update_restaurant():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    restaurant_id = data.get('restaurant_id')
    updates = {k: v for k, v in data.items() if k in ['name', 'address', 'cuisine_type', 'contact_number'] and v}
    if not restaurant_id or not updates:
        return jsonify({'error': 'Missing fields'}), 400
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        set_clause = ", ".join(f"{key}=%s" for key in updates)
        values = list(updates.values()) + [restaurant_id]
        cursor.execute(f"UPDATE Restaurants SET {set_clause} WHERE restaurant_id = %s", values)
        conn.commit()
        return jsonify({'message': '✅ Restaurant updated'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🧹 Admin: Delete Restaurant
@app.route('/admin/delete-restaurant', methods=['POST'])
def delete_restaurant():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    restaurant_id = request.get_json().get('restaurant_id')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Restaurants WHERE restaurant_id = %s", (restaurant_id,))
        conn.commit()
        return jsonify({'message': '✅ Restaurant deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🍽️ Add Menu Item
@app.route('/admin/add-menu-item', methods=['POST'])
def add_menu_item():
    if not session.get('admin') and session.get('role') != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.get_json()
    if session.get('role') == 'restaurant_admin':
        data['restaurant_id'] = session.get('restaurant_id')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Menus (restaurant_id, dish_name, description, price, availability)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['restaurant_id'], data['dish_name'],
            data.get('description'), data['price'],
            data.get('availability', 'In Stock')
        ))
        conn.commit()
        return jsonify({'message': '✅ Menu item added'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ❌ Delete Menu Item
@app.route('/admin/delete-menu-item', methods=['POST'])
def delete_menu_item():
    if not session.get('admin') and session.get('role') != 'restaurant_admin':
        return jsonify({'error': 'Unauthorized'}), 403
    menu_id = request.get_json().get('menu_id')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        if session.get('role') == 'restaurant_admin':
            cursor.execute("DELETE FROM Menus WHERE menu_id = %s AND restaurant_id = %s", (menu_id, session['restaurant_id']))
        else:
            cursor.execute("DELETE FROM Menus WHERE menu_id = %s", (menu_id,))
        conn.commit()
        return jsonify({'message': '✅ Menu item deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🗑️ Admin: Delete User
@app.route('/admin/delete-user', methods=['POST'])
def delete_user():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    email = request.get_json().get('emailToDelete')
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        conn.commit()
        return jsonify({'message': '✅ User deleted'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🔍 Get All Restaurants
@app.route('/restaurants', methods=['GET'])
def get_all_restaurants():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Restaurants")
        return jsonify({'restaurants': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# 🔍 Get Menu by Restaurant
@app.route('/menus/<int:restaurant_id>', methods=['GET'])
def get_menu_by_restaurant(restaurant_id):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Menus WHERE restaurant_id = %s AND availability = 'In Stock'", (restaurant_id,))
        return jsonify({'menu': cursor.fetchall()}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ▶️ Run app
if __name__ == '__main__':
    app.run(debug=True)
