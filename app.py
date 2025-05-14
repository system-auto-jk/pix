import uuid
import requests
import base64
import time
import random
import string
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Coloque seu token do Mercado Pago aqui
ACCESS_TOKEN = 'APP_USR-363066985911462-042421-38576d302723e69d52cca9416a5b1ef7-404686712'

# Armazena temporariamente o status de pagamento
payment_status = {}

@app.route('/')
def index():
    return render_template('index.html', qr_code_img_path=None, pix_code=None)

@app.route('/criar_pagamento', methods=['POST'])
def criar_pagamento():
    valor = float(request.form.get('valor'))
    nome = request.form.get('nome', '').strip()
    cpf = request.form.get('cpf', '').strip()
    email = request.form.get('email', '').strip()
    identificador = request.form.get('identificador', '').strip()

    # Generate a unique idempotency key
    timestamp = str(int(time.time()))
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    idempotency_key = f"Testando Pagamento Online_{timestamp}_{random_suffix}"

    # Build the payer object dynamically based on provided fields
    payer = {}
    if email:
        payer["email"] = email
    if nome:
        payer["first_name"] = nome
    if cpf:
        payer["identification"] = {
            "type": "CPF",
            "number": cpf
        }
    # Fallback to default values if no payer info is provided
    if not payer:
        payer = {
            "email": "cliente@email.com",
            "first_name": "Fulano"
        }

    body = {
        "transaction_amount": valor,
        "description": "Testando Pagamento Online",
        "payment_method_id": "pix",
        "payer": payer
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "X-Idempotency-Key": idempotency_key
    }

    response = requests.post("https://api.mercadopago.com/v1/payments", json=body, headers=headers)

    if response.status_code == 201:
        data = response.json()
        qr_base64 = data["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        pix_code = data["point_of_interaction"]["transaction_data"]["qr_code"]
        qr_code_image = base64.b64decode(qr_base64)
        payment_id = data["id"]

        with open("static/qr_code.png", "wb") as img_file:
            img_file.write(qr_code_image)

        payment_status[payment_id] = "pending"

        return render_template('index.html', 
                               qr_code_img_path="static/qr_code.png", 
                               payment_id=payment_id, 
                               pix_code=pix_code,
                               valor=valor,
                               nome=nome if nome else None,
                               cpf=cpf if cpf else None,
                               email=email if email else None,
                               identificador=identificador if identificador else None)
    else:
        return jsonify({"erro": response.json()}), 400

@app.route('/verificar_pagamento/<int:payment_id>')
def verificar_pagamento(payment_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)

    if response.status_code == 200:
        status = response.json()["status"]
        if status == "approved":
            payment_status[payment_id] = "approved"
            return jsonify({"status": "approved"})
        return jsonify({"status": "pending"})
    return jsonify({"status": "erro"}), 400

@app.route('/sucesso')
def sucesso():
    return render_template('success.html')

if __name__ == '__main__':
    app.run(debug=True)