from flask import Flask, request, jsonify, abort
import sqlite3
import os
import hashlib
import json
import uuid

app = Flask(__name__)

def connect_db():
    return sqlite3.connect('data.db')


def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL
        )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )"""
    )
    conn.commit()
    conn.close()


create_table()


def authenticate(token):
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (token,))
        user = cursor.fetchone()
    return user


def generate_token():
    return str(uuid.uuid4())


def create_user(username, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
        conn.commit()

@app.route('/register', methods=['POST'])
def register():
    """Rota para registrar um novo usuário."""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        create_user(username, password)
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

@app.route('/login', methods=['POST'])
def login():
    """Rota para login do usuário e geração de token."""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    with connect_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password_hash))
        user = cursor.fetchone()

    if user:
        token = generate_token()
        return jsonify({"token": token}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.route('/', methods=['POST', 'GET'])
def use_api():
    """Rota principal que recebe e retorna dados da tabela `data`."""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"error": "Authentication token is required"}), 401

  
    user = authenticate(token)
    if not user:
        return jsonify({"error": "Invalid token"}), 401

    try:
        if request.method == "POST":
            value = request.json.get('data')  

            if value is None:
                return jsonify({"error": "No value provided"}), 400

            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO data (value) VALUES (?)', (value,))
                conn.commit()

            return jsonify({"message": "Value added successfully"}), 201

        elif request.method == "GET":
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM data')
                rows = cursor.fetchall()

            values = [{"id": row[0], "data": row[1]} for row in rows]

            return jsonify(values), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
