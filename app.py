=from flask import Flask, request, jsonify
import os

app = Flask(__name__)

leads_found = 0

@app.route('/')
def home():
    return jsonify({
        "status": "OK", 
        "message": "Flask + Telegram Monitor is running!",
        "leads_found": leads_found
    })

@app.route('/webhook-test/Parser', methods=['POST', 'GET'])
def webhook_parser():
    global leads_found
    
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Send POST request with JSON data",
            "total_leads": leads_found
        })
    
    data = request.get_json() or {}
    print(f"Received lead #{leads_found + 1}: {data}")
    
    leads_found += 1
    
    return jsonify({
        "status": "success",
        "message": f"Lead #{leads_found} received",
        "received_data": data,
        "total_leads": leads_found
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    port = 5432
    print(f"Server starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)



