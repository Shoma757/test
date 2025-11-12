from flask import Flask, request, jsonify
import os
import requests
import time

app = Flask(__name__)

leads_found = 0

@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Flask Server is running!",
        "leads_found": leads_found
    })

@app.route('/webhook-test/Parser', methods=['POST'])
def webhook_parser():
    global leads_found
    data = request.get_json()
    print(f"✅ Получен лид #{leads_found + 1}: {data}")
    
    leads_found += 1
    
    return jsonify({
        "status": "success",
        "message": f"Lead #{leads_found} received",
        "received_data": data
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5432))
    print(f"🚀 Flask Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
