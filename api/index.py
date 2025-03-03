from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS

import json, os, re, time

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from web3 import Web3

INFURA_URL = "https://sepolia.infura.io/v3/e4c9334246014e5a8e61e23c7d325dd0"  # Use Goerli if preferred
web3 = Web3(Web3.HTTPProvider(INFURA_URL))

mongo_atlas_uri = "mongodb+srv://marcellsdave0:JK47pUdOHMC0AFvL@inoma.7ey1w.mongodb.net/?retryWrites=true&w=majority&appName=Inoma"

# Create a new client and connect to the server
client = MongoClient(mongo_atlas_uri, server_api=ServerApi('1'))
db = client["inoma"]

app = Flask(__name__)

# Allow all origins (for testing)
CORS(app, origins=["https://tracepoint-780d6.web.app", "http://127.0.0.1:8080"])  

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$", email)

@app.route("/invoice", methods=["POST"])
def get_invoice():
    data = request.get_json()
    invoice_id = data.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "Missing invoice_id"}), 400
    
    invoice = db["invoice"].find_one({"invoice_id": invoice_id})
    if invoice:
        invoice["_id"] = str(invoice["_id"])  # Convert ObjectId to string
        return jsonify(invoice)
    return jsonify({"error": "Invoice not found"}), 404

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    for field in ["email", "txn_hash","business_id", "invoice_id"]:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    email = data['email']
    txn_hash = data['txn_hash']
    business_id = data['business_id']
    invoice_id = data["invoice_id"]

    if web3.is_connected():
        tx_receipt = web3.eth.get_transaction_receipt(txn_hash)

        if tx_receipt:
            if tx_receipt.status == 1:
                #db['transactions'].insert_one({'email': data['email'], 'txn_hash': data['txn_hash'], 'business_id': data['business_id']})

                invoice = db["invoice"].find_one({"invoice_id": invoice_id})
                if invoice:
                    updated_recs = {
                        "status":"succcess",
                        "txn_hash": txn_hash,
                        "business_id": business_id
                    }

                    db.update_one({"invoice_id": invoice_id}, updated_recs)
                else:
                    return jsonify({"error": "Invoice not found"}), 404

                
                return jsonify({'message': 'OK'}), 200
            else:
                return jsonify({"error": f"Transaction not yet confirmed. Try again later."}), 400
    

@app.route('/leave-referral-programme', methods=['POST'])
def leave_referral_programme():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    for field in ["email", "business_id"]:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    email = data['email']
    business_id = data['business_id']

    if not db["referral-agent"].find_one({"email": email, "business_id": business_id }):
        return jsonify({"error": "Your email is not in our referral programme"}), 400  
    
    db['referral-agent'].delete_one({"business_id": business_id, "email": email})
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/join-referral-programme', methods=['POST'])
def join_referral_programme():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    for field in ["email", "name", "business_id"]:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    email = data['email']    
    name = data['name']
    eth_address = data["eth_address"]
    business_id = data['business_id']
    referral_code = os.urandom(5).hex()

    if db["referral-agent"].find_one({"email": email, "business_id": business_id }):
        return jsonify({"error": "Your email already exists in our referral programme"}), 400  
        
    db['referral-agent'].insert_one({"business_id": business_id, "name": name, "email": email, "referral_code": referral_code, "eth_address": eth_address})
    return jsonify({"message": "OK", "email": email, "name": name, "referral_code": referral_code, "eth_address": eth_address}), 200

@app.route('/get-referral-code', methods=['POST'])
def get_referral_code():
    referral_agents = db['referral-agent']

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    for field in ["email",  "business_id"]:
        if field not in data:
            return jsonify({"error": f"Missing {field}"}), 400

    email = data['email']    
    business_id = data['business_id']

    # Find the referral agent by email and business_id
    agent = referral_agents.find_one({"email": email, "business_id": business_id})

    if not agent:
        return jsonify({"error": "Referral code not found"}), 404

    return jsonify({
        "message": "OK",
        "email": agent["email"],
        "referral_code": agent["referral_code"],
        "business_id": agent["business_id"]
    }), 200

@app.route('/subscribe_mail', methods=['POST'])
def add_to_mailinglist():
    mailinglist = db['mailing-list']

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']    
    business_id = data['business_id']

    if not mailinglist.find_one({'email': email, 'business_id': business_id}):
        mailinglist.insert_one({'email': email, 'business_id': business_id})
    else:
        return jsonify({"error": "Your email already exists in our mailing list"}), 400
    
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/unsubscribe_mail', methods=['POST'])
def remove_from_mailinglist():
    mailinglist = db['mailing-list']

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing Email Field"}), 400
    
    email = data['email']    
    business_id = data['business_id']

    if mailinglist.find_one({'email': email, 'business_id': business_id}):
        mailinglist.delete_one({'email': email, 'business_id': business_id})
    else:
        return jsonify({"error": "Your email was not found in our mailing list"}), 400
    
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/add_to_waitlist', methods=['POST'])
def add_to_waitlist():
    waitlist = db["waitlist"]

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    business_id = data['business_id']
    
    if not waitlist.find_one({'email': email, 'business_id': business_id}):
        waitlist.insert_one({'email': email, 'business_id': business_id})
    else:
        return jsonify({"error": "Your email already exists in our wait-list"}), 400
    
    return jsonify({"message": "OK", "email": email}), 200

@app.route('/remove_from_waitlist', methods=['POST'])
def remove_from_waitlist():
    waitlist = db['waitlist']

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    business_id = data['business_id']

    if waitlist.find_one({'email': email, 'business_id': business_id}):
        waitlist.delete_one({'email': email, 'business_id': business_id})
    else: 
        return jsonify({"error": "Your mail not found in our wait-list"}), 404
    
    return jsonify({"message": "Removed", "email": email}), 200

@app.route('/receive_enquiry', methods=['POST'])
def receive_enquiry():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    required_fields = ['name', 'email', 'message']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    email = data['email']
    data["status"] = "unread"
    data["date"] = time.ctime()

    db["enquiry"].insert_one(data)    
    return jsonify({"message": "Enquiry received"}), 200

@app.route('/request_demo', methods=['POST'])
def request_demo():
    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()

    required_fields = ['name', 'email']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing {field} field"}), 400
    
    email = data['email']
    data["status"] = "unread"
    data["date"] = time.ctime()

    db["demo-request"].insert_one(data)
    return jsonify({"message": "Demo request received"}), 200

if __name__ == '__main__':
    app.run(debug=True)
   