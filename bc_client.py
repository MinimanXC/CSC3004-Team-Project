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
NEW_BLOCK_AVAIL = "new_block_available"
TEMP_NEW_BLOCK = "temp_new_block"
REQUEST_LOCK = "request_lock"
REQUEST_BLOCKCHAIN = "request_blockchain"
BLOCKCHAIN_BACKUP = "blockchain_backup"
BLOCKCHAIN_COPY = "blockchain_copy"
BLOCKCHAIN_ACK = "blockchain_ack"
BLOCKCHAIN_PATH = "savedChain.bc" # To change to persistent storage directory before deployment 

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

        # Error preventing and self healing functions
        self.clearDeadlocks()
        self.request_blockchain()

        #self.pollRequest()
        self.poll_new_block()

        self.past_block_doc = {}
        # self.main()

    def main(self):
        #self.check_new_user() # Function renamed
        self.request_lock() # Request lock from server if want to add block to blockchain
        self.check_lock() # Check if lock is available (0) or not (-1)
        #self.send_new_block_details() # Send details to be added to new block
        self.poll_new_block()

        while True:
            time.sleep(2)
    
    # ====== 1. Execute after user successfully login ======
    # Renamed function from check_new_user to request_blockchain
    # NEW:
    # Make a request to the server to send a copy of their blockchain over to either self heal or update client blockchain
    # OLD:
    # Check if copy of Blockchain exists on client's machine (if new user or not)
    # If not, make a request to server to send a copy over
    def request_blockchain(self):
        #if not (os.path.exists(BLOCKCHAIN_PATH)): # If condition removed to favour self healing and update
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
                # self.request_lock(self.curr_client_id) # Request for lock again 
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
        print(f'> Current lock: {self.lock}, Client: {self.lock_client}')

        # Ensure lock is set to not available (-1) and assigned client is this client before releasing callback
        if self.lock == -1 and self.lock_client == self.curr_client_id:
            self.lock_client = self.curr_client_id
            self.callback_done.set()
    
    # ====== 3. Execute when lock has been acquired and assigned to this user ======
    # Block details will be added to a temporary field before 
    def send_new_block_details(self, client_id, data, image=""):
        self.curr_client_id = client_id
        new_block = self.db.collection(BLOCK_COLL).document(TEMP_NEW_BLOCK) # For filling new block to add

        # !! Note: image_link is a link to receipt by delivery partner
        # Image itself should be first uploaded to Firestore Storage and the link should be placed into the 'image_link' field
        new_block_details = {
            'client_id' : client_id, 
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
        # available = doc_snapshot[0].get('new_available')
        # if available > 0:
        for change in changes:
            # Further execute only if the change are caused by a modify to a value (ignoring adding/deleting of document)
            if change.type.name == 'ADDED' or change.type.name == 'MODIFIED': 
                if doc_snapshot:
                    # hv_received = self.check_received_block_ack()
                    # print("Previously Received Current Block to Add: ", hv_received)
                    # if not hv_received:
                    #     hv_received = True
                    self.get_new_block()
                    
                    self.new_block_callback_done.set()

                    print("[Added new block to Blockchain] Sent acknowledgement! ")

    # Check if client has already acknowledge receive current block 
    def check_received_block_ack(self):
        self.ack_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_ACK)
        client_id=self.curr_client_id.split('@')[0]
        ack_key = str(client_id+'_ack')

        try:
            ack_count = self.ack_doc.get().get(ack_key)
            if ack_count != 0:
                return True # Received
        except:
            print("Have not received")
            return False # Yet to add

    def get_new_block(self):
        new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK).get()

        # Check that data exists and was not previously detected
        if new_block_doc.exists and self.past_block_doc != new_block_doc.to_dict():
            self.past_block_doc = new_block_doc.to_dict()
            print("================== NEW DATA ==================")
            print(self.past_block_doc)
            
            # Add block to existing Blockchain
            try:
                with open(BLOCKCHAIN_PATH, 'rb') as bc_file:
                    bc = pickle.load(bc_file)
            
                new_block = Block(new_block_doc.to_dict())
                bc.addBlock(new_block)

                with open(BLOCKCHAIN_PATH, 'wb') as bc_file:
                    pickle.dump(bc, bc_file)
                
                # Add ack count
                self.ack_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_ACK)
                client_id=self.curr_client_id.split('@')[0]
                ack_key = str(client_id+'_ack')
                self.ack_doc.update({ ack_key: 1 })
                print("Ack: ", ack_key)

                # Upload blockchain blob to cloud for backup purposes (NEW)
                bcBlob = pickle.dumps(bc, protocol=pickle.HIGHEST_PROTOCOL)
                requestBackupColl = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).collection('savedChain.bc').document(str(self.curr_client_id))
                #requestBackupColl = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).collection('savedChain.bc').document('syabil@xavier.com') # This line is for testing purposes
                requestDetails = {
                    'request_time' : firestore.SERVER_TIMESTAMP,
                    'blockchain' : bcBlob,
                    'clientID' : self.curr_client_id
                }
                requestBackupColl.set(requestDetails)
                print("Uploaded blockchain backup to Firebase!")

            except:
                print("error occurred creating new block")


    # 5. Returns the Blockchain saved in .bc file
    def get_saved_blockchain(self):
        with open(BLOCKCHAIN_PATH, 'rb') as bc_file:
            bc = pickle.load(bc_file)

        return bc

    def clearDeadlocks(self):
        lock = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL).get()
        availability = (lock.to_dict()).get('lock')
        lock_client = (lock.to_dict()).get('assigned_client')

        # If the lock is unavailable but the lock belongs to me on boot
        if availability == -1 and self.curr_client_id == lock_client:
            # Call the function to release the lock
            self.complete_sending()

if __name__ == '__main__':
    bc_client()
