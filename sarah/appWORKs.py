from flask import Flask, request, jsonify, session
import mysql.connector
from mysql.connector import Error
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = 'supersecretkey123!'  # 🔐 Replace with a secure key in production

# MySQL Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '7MDAHfa6mah()',
    'database': 'user_system'
}

# 🟢 Register route
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    address = data.get('address')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')

    print(f"📝 Registering: {name}, {email}")
    if not name or not address or not phone or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO users (name, address, phone, email, password)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (name, address, phone, email, password))
        conn.commit()
        return jsonify({'message': '✅ Registered successfully'}), 200
    except Error as e:
        if 'Duplicate' in str(e):
            return jsonify({'error': 'Email already exists'}), 409
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 🔐 Login route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    print(f"🟡 Attempting login for: {email}")

    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    # 🛡️ Admin bypass login
    if email == 'admin@a.a' and password == '123':
        session['admin'] = True
        print("🛡️ Admin login successful")
        return jsonify({'message': '✅ Admin login successful', 'role': 'admin'}), 200

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, password FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            session['email'] = email
            session['name'] = user['name']
            return jsonify({
                'message': '✅ Login successful',
                'role': 'user',
                'email': email,
                'name': user['name']
            }), 200
        else:
            return jsonify({'error': '❌ Invalid email or password'}), 401
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 👤 Get user info
@app.route('/get-user', methods=['GET'])
def get_user():
    email = session.get('email')
    if not email:
        return jsonify({'error': 'User not logged in'}), 401

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT name, address, phone, email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            return jsonify({'user': user}), 200
        return jsonify({'error': 'User not found'}), 404
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# ✏️ Update profile
@app.route('/update-profile', methods=['POST'])
def update_profile():
    if 'email' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    name = data.get('name')
    address = data.get('address')
    phone = data.get('phone')
    email = session['email']

    if not name or not address or not phone:
        return jsonify({'error': 'Missing fields'}), 400

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        update_query = """
            UPDATE users SET name = %s, address = %s, phone = %s WHERE email = %s
        """
        cursor.execute(update_query, (name, address, phone, email))
        conn.commit()
        session['name'] = name
        return jsonify({'message': '✅ Profile updated successfully'}), 200
    except Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# 🚪 Logout
@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200

# 🔎 Session user
@app.route('/session-user', methods=['GET'])
def session_user():
    if 'email' in session:
        return jsonify({
            'email': session['email'],
            'name': session.get('name'),
            'role': 'admin' if session.get('admin') else 'user'
        }), 200
    elif session.get('admin'):
        return jsonify({'email': 'admin@a.a', 'name': 'Admin', 'role': 'admin'}), 200
    else:
        return jsonify({'error': 'No user logged in'}), 401

# ▶️ Run
if __name__ == '__main__':
    app.run(debug=True)
