from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello World!'

@app.route('/test')
def test():
    return 'Test page works!'

@app.route('/webhook-test/Parser')
def webhook():
    return 'Webhook works!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)