from flask import Flask, jsonify, request
from google_drive_uploader_downloader import upload_file, download_file
import json, os, re

app = Flask(__name__)

def dump_json(data, filename):
    with open(filename, 'w') as json_file:
        json.dump(data, json_file, indent=4)

def load_json(filename):
    try:
        if not os.path.exists(filename):
            with open(filename, 'w') as json_file:
                json.dump({}, json_file)

        with open(filename, 'r') as json_file:
            return json.load(json_file)
    except Exception as e:
        print(f"Error loading JSON from {filename}: {e}")
        return {}

waitlist_file_id = ""
enquiries_file_id = ""

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$", email)

def get_waitlist():
    if os.environ.get("APP_STATUS") == "dev":
        return load_json("waitlist.json")

    download_file(waitlist_file_id, "waitlist.json")
    return load_json("waitlist.json")

def update_waitlist(waitlist):
    dump_json(waitlist, "waitlist.json")
    if os.environ.get("APP_STATUS") != "dev":
        upload_file("waitlist.json", "text/json")

def create_enquiry_file(filename, enquiry):
    if os.environ.get("APP_STATUS") == "dev":
        os.makedirs("enquiries", exist_ok=True)
        dump_json(enquiry, f"enquiries/{filename}")
    else:
        enquires_folder_id = ""
        upload_file(filename, "text/json", folder_id=enquires_folder_id)

@app.route('/add_to_waitlist', methods=['POST'])
def add_to_waitlist():
    waitlist = get_waitlist()

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400
    
    business_id = data['business_id']
    if business_id not in waitlist:
        waitlist[business_id] = []

    if email not in waitlist[business_id]:
        waitlist[business_id].append(email)
    
    update_waitlist(waitlist)
    
    return jsonify({"message": "OK", "email": email})

@app.route('/remove_from_waitlist', methods=['POST'])
def remove_from_waitlist():
    waitlist = get_waitlist()

    if not request.is_json:
        return jsonify({"error": "Invalid JSON request"}), 400
    
    data = request.get_json()
    if 'email' not in data or 'business_id' not in data:
        return jsonify({"error": "Missing email or business_id"}), 400
    
    email = data['email']
    business_id = data['business_id']

    if business_id not in waitlist or email not in waitlist[business_id]:
        return jsonify({"error": "Email not found in waitlist"}), 404
    
    waitlist[business_id].remove(email)
    update_waitlist(waitlist)
    return jsonify({"message": "Removed", "email": email})

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
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400   

    enquiry_filename = os.urandom(5).hex() + ".json"
    #dump_json(data, enquiry_filename)
    create_enquiry_file(enquiry_filename, data)
    
    return jsonify({"message": "Enquiry received", "data": data})

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
    #if not is_valid_email(email):
    #    return jsonify({"error": "Invalid email format"}), 400
    
    demo_request_filename = os.urandom(5).hex() + "_demo.json"
    #dump_json(data, demo_request_filename)
    create_enquiry_file(demo_request_filename, data)
    
    return jsonify({"message": "Demo request received", "data": data})

if __name__ == '__main__':
    app.run(debug=True)
