"""
Servidor simplificado do Dumont Cloud para ambiente local
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuração básica
app.config["DEBUG"] = True
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend running"})

@app.route("/api/auth/login", methods=["POST"])
def login():
    return jsonify({
        "success": True,
        "token": "demo-token-123",
        "user": {
            "email": "marcosremar@gmail.com",
            "name": "Marcos",
            "role": "admin"
        }
    })

@app.route("/api/instances", methods=["GET"])
def get_instances():
    return jsonify([])

@app.route("/api/dashboard/metrics", methods=["GET"])
def get_metrics():
    return jsonify({
        "active_instances": 0,
        "total_savings": 0,
        "uptime": "99.9%"
    })

if __name__ == "__main__":
    print("🚀 Dumont Cloud Backend iniciado em http://0.0.0.0:8000")
    print("📊 Modo: DEMO/LOCAL")
    app.run(host="0.0.0.0", port=8000, debug=True)
