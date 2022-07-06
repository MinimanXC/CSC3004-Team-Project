from base64 import decode
from http import client

import firebase_admin
from flask import Flask, render_template, session, request, redirect, flash, jsonify
from blockchain import *
from flask_cors import CORS
from firebase_admin import credentials, firestore
import pyrebase
import json
from bc_client import bc_client
import threading 
import ast
import os

app = Flask(__name__)
cors = CORS(app)

config = {
    'apiKey': "AIzaSyDjbEhtZXFg1hvxkMAeum_N5p7aKAyegvE",
    'authDomain': "csc3004-blockchain.firebaseapp.com",
    'projectId': "csc3004-blockchain",
    'storageBucket': "csc3004-blockchain.appspot.com",
    'messagingSenderId': "474700916812",
    'appId': "1:474700916812:web:d516a61400fc60997c2ce9",
    'measurementId': "G-ZCET6LWY8J",
    'databaseURL': ""
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()
storage = firebase.storage()
cred = credentials.Certificate("firebase-auth.json")
#firebase_admin.initialize_app(cred)
db = firestore.client()

app.secret_key = 'secret'
curr_user = ''
user_type = ''
curr_email = ""
bc = ''

# password for all emails are: 123456
# show different user home page after according to user type
@app.route('/', methods=['POST', 'GET'])
def login():
    if 'user' in session:
        global curr_email
        curr_email = session['user']
        return redirect('home')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = email
            curr_email = email
            print(curr_email)
            users_col = db.collection('users').get()
            for userz in users_col:
                if ((userz.to_dict()).get('user_email') == curr_email):
                    global user_type
                    user_type = (userz.to_dict()).get('user_type')
                    print(user_type)
                    if(user_type == 'client'):
                        return redirect('home')
                    elif (user_type == 'supplier'):
                        return redirect('seller_orders')
                    elif (user_type == 'delivery_partner'):
                        return redirect('delivery')
            flash('Error Retrieving User Info')
            return redirect('login')
        except:
            flash('Failed to login')
    return render_template('login.html')



@app.route('/home', methods=['POST', 'GET'])
def home():
    global curr_user
    curr_user = session['user'] # For getting client id for requesting/assigning of lock (to add block)
    global bc
    bc = bc_client(curr_user)

    # Checks if current user already has a copy of the blockchain, if not, 
    # This function will request it from Server
    bc.check_new_user()

    print(user_type)
    # show different home page based on user type
    if user_type == 'supplier':
        return redirect('seller_orders')
    elif user_type == 'delivery_partner':
        return redirect('delivery')
    return render_template('home.html')

@app.route("/receiver", methods=["POST", 'GET'])
def submit_order():
    data = request.get_data()
    initial_list = json.loads(data.decode("utf-8"))
    print(initial_list)
    orders_dict = {x[0]: x[1] for x in initial_list}
    print(orders_dict)
    new_values = {
        "client_email": curr_email,
        "status": "pending",
        "products": orders_dict
    }
    db.collection("orders").add(new_values)


    print("Data: ", str(data), "\nUser: ", curr_user)
    decoded_dict = orders_dict # Decode bytes data and convert to dictionary

    # Use Threading as there will be multiple functions being executed tied to callback functions
    add_data_thread = threading.Thread(target=add_data_to_blockchain, args=(curr_user,decoded_dict,))
    add_data_thread.daemon = True
    add_data_thread.start()

    # add to firestore

    return data


# Decode bytes data received from request and convert it to a list
# The list format is --> [medicine, price], thus will then be converted to a dictionary
def convert_data_to_dict(data):
    decoded_data = ast.literal_eval(data.decode('UTF-8'))
    res_dict = {decoded_data[i]: decoded_data[i + 1] for i in range(0, len(decoded_data), 2)}

    return res_dict

# Will request lock from server first before a new block's data is sent over to the server
def add_data_to_blockchain(user, data):
    global bc
    if bc == "": # in the event that bc_client was not properly initialised
        global curr_user
        curr_user = session['user']
        bc = bc_client(curr_user)

    bc.request_lock(user)
    lock = bc.check_lock()
    if lock:
        bc.send_new_block_details(user, data)

# View for 'History' page which shows all the blocks in the Blockchain
@app.route('/index')
def blockchain_view():
    global bc
    if bc == '': # in the event that bc_client was not properly initialised
        global curr_user
        curr_user = session['user']
        bc = bc_client(curr_user)

    chainList = ""
    try:
        blockchain = bc.get_saved_blockchain()
        chainList = blockchain.getChain()
    except:
        print("Error occurred trying to read blockchain data")
    
    return render_template('index.html', data=chainList[::-1])

@app.route('/invalidatebc', methods=["POST", 'GET'])
def invalidate_blockchain():
    # Use Blockchain that has already been saved in .bc file
    blockchain = bc.get_saved_blockchain()

    print("!!! Breaking Chain")
    blockchain.breakChain()

    # Get the Blockchain that was modified
    chainList = blockchain.getChain()
    blockchain_len = len(chainList)

    # Perform check to get which block was modified
    is_valid = blockchain.isValid()
    tampered = blockchain.tamperedCount

    # Get the hash and data of modified block to update the block's view on UI
    tampered_block_hash = chainList[blockchain_len - tampered - 1]._hash
    tampered_block_data = chainList[blockchain_len - tampered - 1]._data

    print("Blockchain Validity: ", is_valid, " Tampered Block: ", tampered)

    # Return data back to JavaScript function that called this function
    return jsonify(is_valid, tampered, tampered_block_hash, tampered_block_data)

# allows delivery driver to update delivery status
@app.route('/delivery', methods=['GET', 'POST'])
def update_delivery():
    request_orders_for_delivery = db.collection("orders").get()
    order_details = []
    # filter orders by approved and delivered
    for order in request_orders_for_delivery:
        orders = db.collection('orders').document(order.id).get()
        order_status = (orders.to_dict()).get('status')
        print(order_status)
        if order_status == 'approved' or order_status == 'delivered':
            print(db.collection("orders").document(order.id).collection('status').get())
            order_id = {"id": order.id}
            otd = order.to_dict()
            new_val = {**otd, **order_id}
            order_details.append(new_val)
    if request.method == 'POST':
        oid = request.form.get('oid')
        # uploads shipping photo
        upload = request.files['upload']
        photo_str = 'proof_of_delivery/' + oid + '.jpg'
        print(photo_str)
        storage.child(photo_str).put(upload)

        # updates shipping status
        db.collection("orders").document(oid).update({"status": "delivered"})
        flash('Order is delivered!')
        return redirect('delivery')

    return render_template('delivery.html', data=order_details)


# displays orders made by clients and show the order status
@app.route('/customer_orders', methods=['GET', 'POST'])
def customer_orders():
    request_customer_orders = db.collection("orders").get()
    order_details = []

    for order in request_customer_orders:
        if order.to_dict().get('client_email') == curr_email:
            order_id = {"id": order.id}
            otd = order.to_dict()
            new_val = {**otd, **order_id}
            order_details.append(new_val)

    return render_template('customer_orders.html', data=order_details)


@app.route('/seller_orders', methods=['GET', 'POST'])
def seller_orders():
    request_seller_orders = db.collection("orders").get()
    order_details = []

    for order in request_seller_orders:
        order_id = {"id": order.id}
        otd = order.to_dict()
        new_val = {**otd, **order_id}
        order_details.append(new_val)

    if request.method == 'POST':
        # updates shipping status
        oid = request.form.get('oid')
        print(oid)
        if request.form.get('approve') == 'approve':
            db.collection("orders").document(oid).update({"status": "approved"})
            flash('Order is approved!')
            return redirect('seller_orders')
        elif request.form.get('cancel') == 'cancel':
            db.collection("orders").document(oid).update({"status": "cancelled"})
            flash('Order is cancelled!')
            return redirect('seller_orders')

    return render_template('seller_orders.html', data=order_details)


# logout and clears session
@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True,host=os.getenv('IP', '0.0.0.0'), port=int(os.getenv('PORT', 4444)))