from http import client
from flask import Flask, render_template, session, request, redirect, flash, jsonify
from blockchain import *
from flask_cors import CORS
import pyrebase
from bc_client import bc_client
import threading 

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

bc = bc_client()

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
    bc.check_new_user()
    # bc.poll_new_block()
    return render_template('home.html')


@app.route("/receiver", methods=["POST", 'GET'])
def postME():
    data = request.get_data()
    print(str("dsadssad") + str(data))
    curr_user = session['user']

    add_data_thread = threading.Thread(target=add_data_to_blockchain, args=(curr_user,data,))
    add_data_thread.daemon = True
    add_data_thread.start()
    
    # uid = auth.get_account_info(user['idToken'])

    return data

def add_data_to_blockchain(user, data):
    bc.request_lock(user)
    lock = bc.check_lock()
    if lock:
        bc.send_new_block_details(user, data)

@app.route('/index')
def hello_world():
    # ====== To replace with viewing data from .bc file
    # blockchain = Blockchain()
    # testData = ["Ligma", "Sugma", "Sawcon", "Kisma", "Dragon"]

    # for i in range(5):
    #     blockchain.addBlock(Block(testData[i]))

    # blockchain.printChain()

    blockchain = bc.get_saved_blockchain()
    chainList = blockchain.getChain()
    
    return render_template('index.html', data=chainList[::-1])


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
