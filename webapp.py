from base64 import decode
from http import client
from flask import Flask, render_template, session, request, redirect, flash, jsonify
from blockchain import *
from flask_cors import CORS
import pyrebase
from bc_client import bc_client
import threading 
import ast

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

app.secret_key = 'secret'
curr_user = ''
bc = ''

@app.route('/', methods=['POST', 'GET'])
def login():
    if ('user' in session):
        return redirect('home')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session['user'] = email
            return redirect('home')
        except:
            flash('Failed to login')
    return render_template('login.html')


@app.route('/home', methods=['POST', 'GET'])
def home():
    global curr_user
    curr_user = session['user']
    global bc
    bc = bc_client(curr_user)
    bc.check_new_user()
    
    return render_template('home.html')

@app.route("/receiver", methods=["POST", 'GET'])
def postME():
    data = request.get_data()
    print("Data: ", str(data), "\nUser: ", curr_user)
    decoded_dict = convert_data_to_dict(data)

    add_data_thread = threading.Thread(target=add_data_to_blockchain, args=(curr_user,decoded_dict,))
    add_data_thread.daemon = True
    add_data_thread.start()
    
    # uid = auth.get_account_info(user['idToken'])

    return data

def convert_data_to_dict(data):
    decoded_data = ast.literal_eval(data.decode('UTF-8'))
    print(decoded_data)
    res_dict = {decoded_data[i]: decoded_data[i + 1] for i in range(0, len(decoded_data), 2)}
    print(res_dict)
    return res_dict

def add_data_to_blockchain(user, data):
    global bc
    if bc == "":
        global curr_user
        curr_user = session['user']
        bc = bc_client(curr_user)

    bc.request_lock(user)
    lock = bc.check_lock()
    if lock:
        bc.send_new_block_details(user, data)

@app.route('/index')
def blockchain_view():
    global bc
    if bc == '':
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
    blockchain = bc.get_saved_blockchain()

    print("!!! Breaking Chain")
    blockchain.breakChain()
    is_valid = blockchain.isValid()
    print("Blockchain Validity: ", is_valid)

    return jsonify(is_valid)

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
