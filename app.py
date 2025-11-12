from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "OK", "message": "Server is running!"})

@app.route('/webhook-test/Parser', methods=['GET', 'POST', 'OPTIONS'])
def webhook_parser():
    """Webhook для n8n (поддерживает GET и POST)"""
    
    if request.method == 'GET':
        return jsonify({
            "status": "ready", 
            "message": "Send POST request with JSON data"
        })
    
    # POST запрос
    data = request.get_json(silent=True) or {}
    print(f"✅ Получен POST запрос: {data}")
    
    return jsonify({
        "status": "success",
        "message": "Data received via POST",
        "received_data": data,
        "method": "POST"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
