''' === TO-DO ===
- Runs own copy of Blockchain Server

• Locks
	◦ Make sure the Firebase lock is 0 before requesting to add details for a new block
	◦ Once lock is granted by server

• Acquire lock from server

• New Blocks 
	◦ Poll and check if there’s any new block added to Firebase by Server 
	◦ Point 4 and Point 1

• Acknowledgement
	◦ Change acknowledgement on Firebase to 0 - point 2
	◦ Ensures sync-ed Blockchain on all clients

Process:
1) User wants to add new block to blockchain
2) System request lock from server
3) Continue to next step only if system polls that lock is available (0) and assigned_client is the current client
4) Since assigned client is current client, add new block to 'temp_new_block'
'''

try:
    import time
    from datetime import datetime
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

        self.main()

    def main(self):
        self.request_lock() # Request lock from server
        self.check_lock() # Check if lock is available (0) or not (-1)
        self.send_new_block_details() # Send details to be added to new block

    def check_lock(self):
        print('Checking Lock State')
        items = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL).get()
        self.lock = (items.to_dict()).get('lock')
        self.lock_client = (items.to_dict()).get('assigned_client')
        print('> Current Lock State: ', self.lock)
        
        # Getting realtime updates to check on lock if its unavailable
        if (self.lock != 0 or self.lock_client != self.curr_client_id):

            print('\nLock is currently unavailable, will poll for changes ')
            self.poll_lock()
            while (self.lock != 0 or self.lock_client != self.curr_client_id):
                time.sleep(2)

                # Wait for change in lock value before executing adding details to temp_new_block
        
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

        # Ensure lock is available (0) and assigned client is this client before releasing callback
        if (self.lock == 0 and self.lock_client == self.curr_client_id):
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
    
    def complete_sending(self):
        lock_doc = self.db.collection(BLOCK_COLL).document(LOCK_AVAIL) # For changing assigned_client to None and last_client to this client
        lock_doc.update(
            {
                u'assigned_client': "",
                u'last_change': firestore.SERVER_TIMESTAMP,
                u'last_client': self.curr_client_id,
                u'lock': 0
            }
        )

        print("Sent completion of adding New Block Details! ")

if __name__ == '__main__':
    bc_client()
