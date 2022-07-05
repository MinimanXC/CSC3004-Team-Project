''' === TO-DO ===
- Runs own copy of Blockchain Server

• [Done] Locks
	◦ To add new block, user must request for lock from server
	◦ Once lock is granted by server send new block details to 'temp_new_details'
    ◦ Once done, release lock by changing lock value to available (0) and 'assigned_client' to nothing
        - Server will know that client has released the lock

• New Blocks 
	◦ Poll and check if there’s any new block added to Firebase by Server [Done]
    ◦ Add Block to client's copy of the Blockchain

• [Done] Acknowledgement
	◦ Increase acknowledgement on Firebase - to tell server that client has received the new block
	◦ Ensures sync-ed Blockchain on all clients

• New user to the (Blockchain) system
    ◦ Check if copy of blockchain exists in system
    ◦ If doesn't exist, request download from server

Process:
1) User wants to add new block to blockchain
2) System request lock from server
3) Continue to next step only if system polls that lock is assigned (-1) and 'assigned_client' is the current client
4) Since assigned client is current client, add new block to 'temp_new_block'

'''

try:
    from firebase_admin import credentials, firestore
    from blockchain import Blockchain, Block
    from datetime import datetime

    import os
    import time
    import pickle
    import threading
    import firebase_admin

    print("Dependencies loaded successfully")
except:
    print("Failed to load dependencies")

# DB constants
BLOCK_COLL = "blocks"
LOCK_AVAIL = "lock_availability"
NEW_BLOCK = "new_block"
NEW_BLOCK_ACK = "new_block_ack"
TEMP_NEW_BLOCK = "temp_new_block"
REQUEST_LOCK = "request_lock"
REQUEST_BLOCKCHAIN = "request_blockchain"
REQUEST_COPY = "request_copy"
BLOCKCHAIN_COPY = "blockchain_copy"
BLOCKCHAIN_ACK = "blockchain_ack"
BLOCKCHAIN_PATH = "blockchain.bc" # To change to persistent storage directory before deployment 

try:
    # Initialise Firebase SDK
    cred = credentials.Certificate("firebase-auth.json")
    firebase_admin.initialize_app(cred)
except:
    print("Error initialising Firebase")
    
class bc_client():

    def __init__(self, client_id=1):
        # Initialize firestore instance
        self.db = firestore.client()

        self.lock = -1
        self.curr_client_id = client_id
        self.user_type = 'client' # Either client or supplier
        self.curr_client = self.user_type + '_' + str(self.curr_client_id)

        self.curr_client_email = 'test@test.com'

        self.pollRequest()
        # self.main()

    def main(self):
        self.check_new_user()
        self.request_lock() # Request lock from server if want to add block to blockchain
        self.check_lock() # Check if lock is available (0) or not (-1)
        #self.send_new_block_details() # Send details to be added to new block
        self.poll_new_block()

        while True:
            time.sleep(2)
    
    # ====== 1. Execute after user successfully login ======
    # Check if copy of Blockchain exists on client's machine (if new user or not)
    # If not, make a request to server to send a copy over
    def check_new_user(self):
        if not (os.path.exists(BLOCKCHAIN_PATH)):
            self.request_blockchain_doc = self.db.collection(BLOCK_COLL).document(REQUEST_BLOCKCHAIN).collection('blockchain_requestors').document(self.curr_client_id)
            bc_request_details = {
                'client_id' : self.curr_client_id,
                'request_time' : firestore.SERVER_TIMESTAMP,
                'user_type': self.user_type
            }

            self.request_blockchain_doc.set(bc_request_details)
            print("\nSent Blockchain Request to Server! ")
            
            self.poll_blockchain_copy()
    
    # Initiate threading to poll for a copy of blockchain sent by server
    def poll_blockchain_copy(self):
        # Create an Event for notifying main Thread
        self.bc_callback_done = threading.Event()
        self.blockchain_copy_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_COPY)

        # Watch the document for changes
        self.blockchain_copy_doc_watch = self.blockchain_copy_doc.on_snapshot(self.on_blockchain_copy_snapshot)
    
    # Callback function to capture blockchain copy sent by server
    def on_blockchain_copy_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            blockchain_copy = doc_snapshot[0].get('bc')
            print('> Received Blockchain copy !')

            with open(BLOCKCHAIN_PATH, 'wb') as handle:
                handle.write(blockchain_copy)

            self.bc_callback_done.set()

            # Send acknowledgement to server that blockchain copy received successfully
            bc_ack_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK).get()
            bc_ack = bc_ack_doc.get('bc_ack')
            self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK).set({'bc_ack': bc_ack+1})

            print('> Sent acknowledgement message !')

    # ====== 2. Execute when user executes an action (thus adding a block to blockchain) ======
    # Request block from server before adding block to temp_block
    def request_lock(self, client_id):
        # Check User collection and assign client an ID
        # Thus, the document to be inserted as in 'requestor' collection will be 'client_<client_id>'
        requestor = 'requestors'
        self.curr_client_id = client_id
        request_lock_coll = self.db.collection(BLOCK_COLL).document(REQUEST_LOCK).collection(requestor).document(self.curr_client_id)
        new_request_details = {
            'client_id' : self.curr_client_id, 
            'request_time' : firestore.SERVER_TIMESTAMP,
            'user_type': self.user_type
        }

        request_lock_coll.set(new_request_details)
        print("\nSent Lock Request to Server! ")

    # ====== 2.1. Execute checking of lock (polling) assigned to this user or not ======
    # Getting updates to check on lock if its available and assigned to this user
    def check_lock(self):
        print('Checking Lock State')
        items = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL).get()
        self.lock = (items.to_dict()).get('lock')
        self.lock_client = (items.to_dict()).get('assigned_client')
        print('> Current Lock State: ', self.lock, 'Assigned client: ', self.lock_client)
        
        if (self.lock != -1 or self.lock_client != self.curr_client_id):

            self.poll_lock() # Set callback
            while self.lock != -1 or self.curr_client_id != self.lock_client:
                time.sleep(2)

                # Ensure lock is -1 and assigned_user is this current user before executing other functions

        if self.lock == -1 and self.curr_client_id == self.lock_client:
            return True

    # Initiate threading to poll for changes to lock_availability document values
    def poll_lock(self):
        # Create an Event for notifying main Thread
        self.callback_done = threading.Event()
        lock_avail_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL)

        # Watch the document for changes
        self.doc_watch = lock_avail_doc.on_snapshot(self.on_lock_snapshot)
    
    # Callback function to capture changes to lock availability
    # If lock is not available (-1) and assigned to this user, then execute the function to send block data to server
    def on_lock_snapshot(self, doc_snapshot, changes, read_time):
        self.lock = doc_snapshot[0].get('lock')
        self.lock_client = doc_snapshot[0].get('assigned_client')
        print(f'> Received lock: {self.lock}, Client {self.lock_client}')

        # Ensure lock is set to not available (-1) and assigned client is this client before releasing callback
        if self.lock == -1 and self.lock_client == self.curr_client_id:
            self.lock_client = self.curr_client_id
            self.callback_done.set()
    
    # ====== 3. Execute when lock has been acquired and assigned this this user ======
    # Block details will be added to a temporary field before 
    def send_new_block_details(self, client_id, data, image=""):
        self.curr_client_id = client_id
        new_block = self.db.collection(BLOCK_COLL).document(TEMP_NEW_BLOCK) # For filling new block to add

        # !! Note: image_link is a link to receipt by delivery partner
        # Image itself should be first uploaded to Firestore Storage and the link should be placed into the 'image_link' field
        new_block_details = {
            'client_id' : self.curr_client_id, 
            'data' : data,
            'timestamp' : firestore.SERVER_TIMESTAMP
        }
        if image != "" : new_block_details['image'] = image 

        new_block.set(new_block_details)
        print("\nSent New Block Details! ")
        self.complete_sending()
    
    # For changing assigned_client to None and last_client to this client
    # Inform server that client has finished executing functions 
    def complete_sending(self):
        lock_avail_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL) 
        lock_avail_doc.update(
            {
                u'assigned_client': "",
                u'last_change': firestore.SERVER_TIMESTAMP,
                u'last_client': self.curr_client_id,
                u'lock': 0
            }
        )

        print("Sent completion of adding New Block Details! ")
        self.poll_new_block()

    # ====== 4. Execute after login to check if server has sent over a new block ======
    # Check if server has sent a new Block to add to Blockchain
    def poll_new_block(self):
        # Create an Event for notifying main Thread
        self.new_block_callback_done = threading.Event()
        self.new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)

        # Watch the document for changes
        self.new_block_doc_watch = self.new_block_doc.on_snapshot(self.on_new_block_snapshot)
    
    # Callback function to capture changes to new_block documents
    # - Add block to client's copy of blockchain 
    # - Send acknowledgement to Firebase
    def on_new_block_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            new_block_to_add = doc_snapshot[0]
            
            # Add block to existing Blockchain
            try:
                with open(BLOCKCHAIN_PATH, 'rb') as bc_file:
                    bc = pickle.load(bc_file)
            
                new_block = Block(new_block_to_add.to_dict())
                bc.addBlock(new_block)

                with open(BLOCKCHAIN_PATH, 'wb') as bc_file:
                    pickle.dump(bc, bc_file)
            except:
                print("error occurred creating new block")
            
            self.new_block_callback_done.set()

            # Increase ack count
            self.ack_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_ACK)
            ack_count = self.ack_doc.get().get('ack')
            self.ack_doc.update({
                'ack': ack_count+1,
                'ack_time': firestore.SERVER_TIMESTAMP
            })
            print("[Added new block to Blockchain] Sent acknowledgement! ")

    # 5. Returns the Blockchain saved in .bc file
    def get_saved_blockchain(self):
        with open(BLOCKCHAIN_PATH, 'rb') as bc_file:
            bc = pickle.load(bc_file)

        return bc

    # Initiate threading to poll for changes to request_copy document values
    def pollRequest(self):
        # Create an Event for notifying main Thread
        self.callbackDone = threading.Event()
        copyReqDoc = self.db.collection(BLOCK_COLL).document(REQUEST_COPY)

        # Watch the document for changes
        self.copyRequestDocWatch = copyReqDoc.on_snapshot(self.onRequestSnapshot)
    
    # Callback function to capture changes to copy request
    def onRequestSnapshot(self, doc_snapshot, changes, read_time):
        try: 
            saveFile = open('savedChain.bc', 'rb') # TODO: Change the file path when using Docker Persistent Storage
            savedChain = pickle.load(saveFile)
             # Serialize Blockchain before sending to Client
            bcBlob = pickle.dumps(savedChain, protocol=pickle.HIGHEST_PROTOCOL)
            requestBackupColl = self.db.collection(BLOCK_COLL).document(REQUEST_COPY).collection('savedChain.bc').document('client_'+str(self.curr_client_id))
            requestDetails = {
                'request_time' : firestore.SERVER_TIMESTAMP,
                'blockchain' : bcBlob
            }
            requestBackupColl.set(requestDetails)
            saveFile.close() # Close the file
            self.callbackDone.set() # Stop the thread
        except:
            print("Client %s has no backup of the chain (or an error occured, please try again)!" % self.curr_client_id)

if __name__ == '__main__':
    bc_client()
