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
BLOCKCHAIN_COPY = "blockchain_copy"
BLOCKCHAIN_ACK = "blockchain_ack"
BLOCKCHAIN_PATH = "blockchain.pickle"

class bc_client():

    def __init__(self):
        # Initialise Firebase SDK
        self.cred = credentials.Certificate("firebase-auth.json")
        firebase_admin.initialize_app(self.cred)
        # Initialize firestore instance
        self.db = firestore.client()

        self.lock = -1
        self.curr_client_id = 1
        self.user_type = 'client' # Either client or supplier
        self.curr_client = self.user_type + '_' + str(self.curr_client_id)

        self.curr_client_email = 'test@test.com'

        self.main()

    def main(self):
        self.check_new_user()
        # self.request_lock() # Request lock from server if want to add block to blockchain
        # self.check_lock() # Check if lock is available (0) or not (-1)
        # self.send_new_block_details() # Send details to be added to new block
        # self.poll_new_block()

        while True:
            time.sleep(2)
    
    # Check if copy of Blockchain exists on client's machine (if new user or not)
    # If not, make a request to server to send a copy over
    def check_new_user(self):
        if not (os.path.exists(BLOCKCHAIN_PATH)):
            self.request_blockchain_doc = self.db.collection(BLOCK_COLL).document(REQUEST_BLOCKCHAIN).collection('blockchain_requestors').document(self.curr_client_email)
            bc_request_details = {
                'client_id' : self.curr_client_email,
                'request_time' : firestore.SERVER_TIMESTAMP,
                'user_type': self.user_type
            }

            self.request_blockchain_doc.set(bc_request_details)
            print("Sent Blockchain Request to Server! ")
            
            self.poll_blockchain_copy()
    
    # Initiate threading to poll for a copy of blockchain sent by server
    def poll_blockchain_copy(self):
        # Create an Event for notifying main Thread
        self.bc_callback_done = threading.Event()
        self.blockchain_copy_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_COPY)

        # Watch the document for changes
        self.blockchain_copy_doc_watch = self.blockchain_copy_doc.on_snapshot(self.on_blockchain_copy_snapshot)
    
    # Callback function to capture changes to lock availability
    def on_blockchain_copy_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            blockchain_copy = doc_snapshot[0].get('bc')
            print(f'> Received Blockchain copy !')

            with open(BLOCKCHAIN_PATH, 'wb') as handle:
                pickle.dump(blockchain_copy, handle, protocol=pickle.HIGHEST_PROTOCOL)

            self.bc_callback_done.set()

            # Send acknowledgement to server that blockchain copy received successfully
            bc_ack_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK).get()
            bc_ack = bc_ack_doc.get('bc_ack')
            self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK).set({'bc_ack': bc_ack+1})

    # Getting updates to check on lock if its available and assigned to this user
    def check_lock(self):
        print('Checking Lock State')
        items = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL).get()
        self.lock = (items.to_dict()).get('lock')
        self.lock_client = (items.to_dict()).get('assigned_client')
        print('> Current Lock State: ', self.lock)
        
        if (self.lock != -1 and self.lock_client != self.curr_client_id):

            self.poll_lock() # Set callback
            while self.lock != -1 and self.curr_client_id != self.lock_client:
                time.sleep(2)

                # Ensure lock is -1 and assigned_user is this current user before executing other functions
        
        return self.lock

    # Initiate threading to poll for changes to lock_availability document values
    def poll_lock(self):
        # Create an Event for notifying main Thread
        self.callback_done = threading.Event()
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL)

        # Watch the document for changes
        self.doc_watch = lock_doc.on_snapshot(self.on_lock_snapshot)
    
    # Callback function to capture changes to lock availability
    def on_lock_snapshot(self, doc_snapshot, changes, read_time):
        self.lock = doc_snapshot[0].get('lock')
        self.lock_client = doc_snapshot[0].get('assigned_client')
        print(f'> Received lock: {self.lock}, Client {self.lock_client}')

        # Ensure lock is set to not available (-1) and assigned client is this client before releasing callback
        if self.lock == -1 and self.lock_client == self.curr_client_id:
            self.lock_client = self.curr_client_id
            self.callback_done.set()
    
    # Request block from server before adding block to temp_block
    def request_lock(self):
        # Check User collection and assign client an ID
        # Thus, the document to be inserted as in 'requestor' collection will be 'client_<client_id>'
        requestor = 'requestors'
        client = 'client_' + str(1)
        request_lock_coll = self.db.collection(BLOCK_COLL).document(REQUEST_LOCK).collection(requestor).document(client)
        new_request_details = {
            'client_id' : 1, 
            'request_time' : firestore.SERVER_TIMESTAMP,
            'user_type': self.user_type
        }

        request_lock_coll.set(new_request_details)
        print("Sent Lock Request to Server! ")
    
    # Block details will be added to a temporary field before 
    def send_new_block_details(self):
        new_block = self.db.collection(BLOCK_COLL).document(TEMP_NEW_BLOCK) # For filling new block to add

        # !! Note: image_link is a link to receipt by delivery partner
        # Image itself should be first uploaded to Firestore Storage and the link should be placed into the 'image_link' field
        new_block_details = {
            'client_id' : 1, 
            'data' : "test",
            'image_link' : "sample image",
            'new_block_details' : "test",
            'timestamp' : firestore.SERVER_TIMESTAMP
        }

        new_block.set(new_block_details)
        print("Sent New Block Details! ")
        self.complete_sending()
    
    # For changing assigned_client to None and last_client to this client
    # Inform server that client has finished executing functions 
    def complete_sending(self):
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL) 
        lock_doc.update(
            {
                u'assigned_client': "",
                u'last_change': firestore.SERVER_TIMESTAMP,
                u'last_client': self.curr_client_id,
                u'lock': 0
            }
        )

        print("Sent completion of adding New Block Details! ")

    # 1. Check if server has sent a new Block to add to Blockchain
    def poll_new_block(self):
        # Create an Event for notifying main Thread
        self.new_block_callback_done = threading.Event()
        self.new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)

        # Watch the document for changes
        self.new_block_doc_watch = self.new_block_doc.on_snapshot(self.on_new_block_snapshot)
    
    # 2. Callback function to capture changes to new_block documents
    # - Add block to client's copy of blockchain 
    # - Send acknowledgement to Firebase
    def on_new_block_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            new_block_to_add = doc_snapshot[0]
            
            # TO-DO: Add block to Blockchain
            
            self.new_block_callback_done.set()

            # Increase ack count
            self.ack_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_ACK)
            ack_count = self.ack_doc.get().get('ack')
            self.ack_doc.update({
                'ack': ack_count+1,
                'ack_time': firestore.SERVER_TIMESTAMP
            })
            print("Sent acknowledgement! ")

if __name__ == '__main__':
    bc_client()
