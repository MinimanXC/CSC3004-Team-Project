''' === TO-DO ===

• Holds write (new block) lock
	◦ Change lock value from 0 to -1
	◦ Same lock mentioned in point 3 above

• Client can request for lock to add new block to blockchain
	◦ Server ensures the client with the earliest timestamp is given lock first
	◦ Once lock is granted to that client, remove timestamp from point 5 in Firebase
		‣ Update lock details in point 3
	◦ Client can then send details of new block to be added to the blockchain to firebase

• If lock is taken, Server will poll for point 6

• With the updated Blockchain (with new block)
	◦ Sends details of new block to Firebase in point 1
	◦ Inform clients that a new block is available by changing data in point 4 

• Once all clients have acknowledged receive of new block data in point 2
	◦ Ensure timestamp of acknowledgement is after the timestamp of when the new block details was added to Firebase, 
	◦ Once all clients acknowledges with 0 and valid timestamp, 
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
BLOCK_COLL = "blocks"
LOCK_AVAIL = "lock_availability"
NEW_BLOCK = "new_block"
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
        self.requests_left = 0
        self.main()

    def main(self):
        print("Done checking Lock Requests")
        self.poll_lock()
        self.poll_requests()

        # Indefinitely check that no one is holding lock or have any requests
        while True:
            time.sleep(2)

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
                print(requests.to_dict())
                requests_list.append(requests.to_dict()) 
                self.requests_left += 1
                
        except Exception as e:
            print("While handling requests: ", e)

        if (requests_list):
            requests_list.sort(key=lambda x:x['request_time']) # sort by earliest request time
            self.earliest_requestor = requests_list[0].get('client_id')
            self.earliest_requestor_type = requests_list[0].get('user_type')
            print(f'> Requestor: {self.earliest_requestor}, Requestor Type: {self.earliest_requestor_type}')
            
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
        self.requests_left -= 1
        print("Removed lock request for: ", requestor)
    
    # Once lock is assigned to a client, poll for changes to the lock and assigned_client field
    # If lock is 0, and assigned_client is empty, means client is done with it's processes
    def poll_lock(self):
        # Create an Event for notifying main Thread
        self.lock_callback_done = threading.Event()
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL)

        # Watch the document for changes
        self.doc_watch = lock_doc.on_snapshot(self.on_lock_snapshot)
    
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

if __name__ == '__main__':
    bc_server()