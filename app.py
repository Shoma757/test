from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Простой webhook для тестирования
@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Telegram Monitor Server is running!",
        "endpoints": {
            "webhook": "POST /webhook-test/Parser",
            "status": "GET /status"
        }
    })

@app.route('/webhook-test/Parser', methods=['GET', 'POST'])
def webhook_parser():
    """Webhook для n8n"""
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Send POST request with JSON data"
        })
    
    data = request.get_json(silent=True) or {}
    print(f"✅ Получены данные в webhook: {data}")
    
    return jsonify({
        "status": "success",
        "message": "Data received via POST",
        "received_data": data
    })

@app.route('/status')
def status():
    return jsonify({
        "status": "running",
        "message": "Flask server is working"
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
