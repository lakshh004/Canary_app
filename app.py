from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "version": os.getenv("APP_VERSION", "v1"),
        "message": "Hello from AKS Canary"
    })

app.run(host='0.0.0.0', port=5000)
