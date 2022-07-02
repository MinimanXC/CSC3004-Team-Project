''' === TO-DO ===

• [Done] Holds write (new block) lock
	◦ Change lock value from 0 to -1
	◦ Once user is done, lock will be changed from -1 to 0

• [Done] Client can request for lock to add new block to blockchain
	◦ Server ensures the client with the earliest timestamp is given lock first
	◦ Once lock is granted to that client, remove request entry in Firebase
		‣ Update/assign lock in point 3
	◦ Client can then send details of new block to temp_new_details to be added to the blockchain to firebase

• [Done] If lock is assigned, Server poll for temp_new_details for new Block's details to be added to Blockchain

• [Done] With the updated Blockchain (with new block)
	◦ Sends details of new block to Firebase in point 1
	◦ Inform clients that a new block is available by changing data in point 4 (Removed since used callback function in Client)

• [Done] Once all clients have acknowledged receive of new block data in point 2 
	◦ Remove the new block details from Firebase.
	◦ Keeping the new block details records empty
'''

# Library imports
try:
    import time
    import threading
    import firebase_admin
    from firebase_admin import credentials, firestore

    print("Dependencies loaded successfully")
except:
    print("Failed to load dependencies")

# DB constants
USERS_COLL = "users"
BLOCK_COLL = "blocks"
LOCK_AVAIL = "lock_availability"
NEW_BLOCK = "new_block"
NEW_BLOCK_ACK = "new_block_ack"
NEW_BLOCK_AVAIL = "new_block_available"
TEMP_NEW_BLOCK = "temp_new_block"
REQUEST_LOCK = "request_lock"

class bc_server():

    def __init__(self):
        # Initialise Firebase SDK
        self.cred = credentials.Certificate("firebase-auth.json")
        firebase_admin.initialize_app(self.cred)
        # Initialize firestore instance
        self.db = firestore.client()

        self.lock = -1
        self.clients_count = 10
        self.main()

    def main(self):
        print("Done checking Lock Requests")
        self.get_num_of_clients()
        self.poll_lock()
        self.poll_requests()
        
        while self.lock != 0:
            time.sleep(2)
            print('Lock: ', self.lock)

        # Indefinitely check that no one is holding lock or have any requests
        while True:
            time.sleep(2)
    
    # Get number of clients currently registered in the system
    # This number will be used for client acknowledgement on receival of New Block added
    def get_num_of_clients(self):
        new_block_doc = self.db.collection(USERS_COLL).get()
        self.clients_count = len(new_block_doc)
        print("Number of Clients: ", self.clients_count)

    # Initiate threading to poll for new requests added to 'request_lock', 'requestors' collection
    # Check for any new requests submitted by client, if yes, process it
    def poll_requests(self):
        # Create an Event for notifying main Thread
        self.requests_callback_done = threading.Event()
        requests_coll = self.db.collection_group('requestors')

        # Watch the document for changes
        self.doc_watch = requests_coll.on_snapshot(self.on_requests_snapshot)
    
    # Callback function to capture changes to lock availability
    def on_requests_snapshot(self, coll_snapshot, changes, read_time):
        requests_list = []

        try:
            for requests in coll_snapshot:
                # print(requests.to_dict())
                requests_list.append(requests.to_dict()) 

        except Exception as e:
            print("While handling requests: ", e)

        if (requests_list):
            requests_list.sort(key=lambda x:x['request_time']) # sort by earliest request time
            self.earliest_requestor = requests_list[0].get('client_id')
            self.earliest_requestor_type = requests_list[0].get('user_type')
            print(f'> Requestor: {self.earliest_requestor}, Requestor Type: {self.earliest_requestor_type}')
            
            # Start polling for client to add Block details to temp_new_block
            self.poll_temp_block()

            # Assign lock to client
            self.assign_lock(self.earliest_requestor)

            # Remove request since lock has been assigned to the client
            self.remove_request_lock(self.earliest_requestor, self.earliest_requestor_type)

        # !! Don't release callback as need to indefinitely check for requests

    # Assign lock to the client through its client id
    def assign_lock(self, client_id):
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL)
        lock_doc.update(
            {
                u'assigned_client': str(client_id),
                u'last_change': firestore.SERVER_TIMESTAMP,
                u'lock': -1
            }
        )
        print("Assigned lock to: ", client_id)
    
    # Once done assigning lock to client, remove its request from the list of requestors
    def remove_request_lock(self, doc_id, user_type):
        request_lock_coll = self.db.collection(BLOCK_COLL).document(REQUEST_LOCK).collection('requestors')
        requestor = str(user_type) + '_' + str(doc_id)

        request_lock_coll.document(requestor).delete()

        print("Removed lock request for: ", requestor)
    
    # Once lock is assigned to a client, poll for changes to the lock and assigned_client field
    # If lock is 0, and assigned_client is empty, means client is done with it's processes
    def poll_lock(self):
        # Create an Event for notifying main Thread
        self.lock_callback_done = threading.Event()
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL)

        # Watch the document for changes
        self.lock_doc_watch = lock_doc.on_snapshot(self.on_lock_snapshot)
    
    # Callback function to capture changes to lock availability
    def on_lock_snapshot(self, doc_snapshot, changes, read_time):
        curr_lock = doc_snapshot[0].get('lock')
        assigned_client = doc_snapshot[0].get('assigned_client')
        print(f'> Current lock: {curr_lock}, Assigned Client: {assigned_client}')

        # Ensure lock is set back to available (0) and assigned client releases the lock before releasing callback
        if (curr_lock == 0 and assigned_client == ''):
            self.lock = curr_lock
            print("Client released lock")
            self.lock_callback_done.set()

    # Get Block that client wants to add to Blockchain
    def poll_temp_block(self):
        # Create an Event for notifying main Thread
        self.temp_block_callback_done = threading.Event()
        self.temp_new_block_doc = self.db.collection(BLOCK_COLL).document(TEMP_NEW_BLOCK)

        # Watch the document for changes
        self.doc_watch = self.temp_new_block_doc.on_snapshot(self.on_temp_block_snapshot)
    
    # Callback function to capture changes to temp_new_block
    # Client will populate this document with details of block to be added to Blockchain
    def on_temp_block_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            temp_block = doc_snapshot[0]
            client_id = temp_block.get('client_id')
            print(f'> Temp Block By: {client_id}')

            if self.earliest_requestor == client_id:
                self.temp_block_callback_done.set()
                self.temp_new_block_doc.delete() # Clear document since will be added to blockchain
                print("Deleted",TEMP_NEW_BLOCK)
            
            self.add_block_to_blockchain(temp_block.to_dict())
        else:
            print("No new Block details")
    
    # Add details provided by client to Blockchain
    def add_block_to_blockchain(self, new_block_dict):
        new_block = {
            'added_time': firestore.SERVER_TIMESTAMP,
            'block_hash': "test this hash",
            'data': new_block_dict,
            'nonce': 12345,
            'prev_hash': "test prev hash"
        }

        ### TO-DO: Execute Functions to add Block to Blockchain

        print("Added Block to Blockchain!")

        # Once Block successfully added to Blockchain, send Block Details to clients
        self.send_block_to_clients(new_block)

    # Send new Block added to Blockchain to Client
    def send_block_to_clients(self, new_block):
        new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)
        new_block_doc.set(new_block)

        new_block_avail_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_AVAIL)
        new_block_avail_doc.set({
            'new_available': 0,
            'block_added_time': firestore.SERVER_TIMESTAMP
        })

        print("Sent Block to Clients! ")

        # Start polling for acknowledgement message sent by clients
        self.poll_ack()

    # Check number of acknowledgements received by clients before deleting new block details
    # If acknowledgment received, client has added the block to its copy of the Blockchain
    def poll_ack(self):
        # Create an Event for notifying main Thread
        self.ack_callback_done = threading.Event()
        self.ack_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK_ACK)

        # Watch the document for changes
        self.ack_doc_watch = self.ack_doc.on_snapshot(self.on_ack_snapshot)
    
    # Callback function to capture changes to lock availability
    def on_ack_snapshot(self, doc_snapshot, changes, read_time):
        curr_ack = doc_snapshot[0].get('ack')

        # Ensure lock is set back to available (0) and assigned client releases the lock before releasing callback
        if (curr_ack == self.clients_count):
            print("Clients ack-ed")
            self.ack_callback_done.set()
            
            # Once all clients have acknowledged, remove block details
            new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)
            new_block_doc.delete()

            self.ack_doc.update({'ack':0})

if __name__ == '__main__':
    bc_server()