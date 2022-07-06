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

• [Done] New user to the (Blockchain) system
    ◦ Client will send a request to server (via Firebase), thus respond to it by sending over the Blockchain data
    ◦ Once client sends an ack, remove its request and ack entry

'''

# Library imports
try:
    import time
    import pickle
    import threading
    import firebase_admin
    from blockchain import Blockchain, Block
    from firebase_admin import credentials
    from firebase_admin import firestore

    print("Dependencies loaded successfully")
except Exception as e:
    print("Failed to load dependencies", e)

# DB constants
USERS_COLL = "users"
BLOCK_COLL = "blocks"
LOCK_AVAIL = "lock_availability"
NEW_BLOCK = "new_block"
NEW_BLOCK_ACK = "new_block_ack"
NEW_BLOCK_AVAIL = "new_block_available"
TEMP_NEW_BLOCK = "temp_new_block"
REQUEST_LOCK = "request_lock"
REQUEST_BLOCKCHAIN = "request_blockchain"
BLOCKCHAIN_BACKUP = "blockchain_backup"
BLOCKCHAIN_ACK = "blockchain_ack"
BLOCKCHAIN_COPY = "blockchain_copy"
SAVEDCHAIN = "../app-data/savedChain.bc"

try:
    # Initialise Firebase SDK
    cred = credentials.Certificate("firebase-auth.json")
    firebase_admin.initialize_app(cred)
except:
    print("Error initialising Firebase")

class bc_server():

    def __init__(self):
        # Initialize firestore instance
        self.db = firestore.client()

        # Attempt to load the chain
        self.blockchain = self.loadChain()

        self.lock = -1
        self.clients_count = 10
        self.main()

    def main(self):
        # print("Done checking Lock Requests")
        self.get_num_of_clients()
        self.poll_blockchain_request()
        self.poll_lock()
        self.poll_requests()
        
        # Indefinitely check that no one is holding lock or have any requests
        while True:
            time.sleep(2)
    
    # Get number of clients currently registered in the system
    # This number will be used for client acknowledgement on receival of New Block added
    def get_num_of_clients(self):
        new_block_doc = self.db.collection(USERS_COLL).get()
        self.clients_count = len(new_block_doc)
        print("Number of Clients: ", self.clients_count)
    
    # Check if a new user is added to system and requested for a copy of the blockchain
    def poll_blockchain_request(self):
        # Create an Event for notifying main Thread
        self.blockchain_req_callback_done = threading.Event()
        self.blockchain_req_doc = self.db.collection_group('blockchain_requestors')

        # Watch the document for changes
        self.blockchain_requestors = []
        self.blockchain_req_doc_watch = self.blockchain_req_doc.on_snapshot(self.on_blockchain_request_snapshot)
    
    # Callback function to capture changes to blockchain requests
    def on_blockchain_request_snapshot(self, doc_snapshot, changes, read_time):
        if doc_snapshot:
            print("\nReceived new blockchain copy request")
            self.blockchain_requestors.append(doc_snapshot[0].id)
            self.no_bc_requestors = len(doc_snapshot) # Count for tallying acknowledgement message

            # Set up acknowledgement document for clients to increase count
            self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK).set({'bc_ack': 0})

            # Start polling for acknowledgement messages sent by clients that has requested for a copy of the blockchain
            self.poll_blockchain_ack() 

            # Initiate sending of entire Blockchain to client
            self.send_blockchain_copy()

            # !! Do not release callback as need to indefinitely check for addition of new users to the system
    
    # Send a copy of the current blockchain to client in pickle format
    def send_blockchain_copy(self):
        # Serialize Blockchain before sending to Client
        bc_to_send = pickle.dumps(self.blockchain, protocol=pickle.HIGHEST_PROTOCOL)

        self.blockchain_copy_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_COPY)
        self.blockchain_copy_doc.set({u'bc': bc_to_send})

        print("Sent Blockchain Copy !")
    
    # Check if clients have acknowledged receipt of Blockchain copy
    def poll_blockchain_ack(self):
        # Create an Event for notifying main Thread
        self.blockchain_ack_callback_done = threading.Event()
        self.blockchain_ack_doc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_ACK)

        self.ack_count = 0 # To ensure that actions relating to client's ack msg are only processed according to the number of ack to receive

        # Watch the document for changes
        self.blockchain_ack_doc_watch = self.blockchain_ack_doc.on_snapshot(self.on_blockchain_ack_snapshot)
    
    # Callback function to capture increase in acknowledge count
    def on_blockchain_ack_snapshot(self, doc_snapshot, changes, read_time):
        for change in changes:
            # Further execute only if the change are caused by a modify to a value (ignoring adding/deleting of document)
            if change.type.name == 'MODIFIED': 
                if doc_snapshot:
                    ack_no = doc_snapshot[0].get('bc_ack')
                    self.ack_count += 1

                    if ack_no == self.no_bc_requestors and self.ack_count == self.no_bc_requestors:
                        print("All requestors has received Blockchain copy")

                        self.remove_blockchain_request()

                        # Remove callback function only when all requestors (clients) have acknowledged
                        self.blockchain_ack_callback_done.set()

    # Remove requests as it has been fulfilled
    def remove_blockchain_request(self):
        self.blockchain_copy_doc.delete()
        for requestors in self.blockchain_requestors:
            self.db.collection(BLOCK_COLL).document(REQUEST_BLOCKCHAIN).collection('blockchain_requestors').document(requestors).delete()
        self.db.collection(BLOCK_COLL).document(REQUEST_BLOCKCHAIN).delete()
        self.blockchain_ack_doc.delete()
        print("Removed Blockchain Request and Acknowledgement")

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
            
            print("\nReceived new lock request")
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
        requestor = str(doc_id)

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
            print(f'> Temp Block By: {client_id}') # TODO: Add count validation check, due to multiple prints

            if self.earliest_requestor == client_id:
                self.temp_block_callback_done.set()
                self.temp_new_block_doc.delete() # Clear document since will be added to blockchain
                print("Deleted",TEMP_NEW_BLOCK)
            
            self.add_block_to_blockchain(temp_block.to_dict())
        else:
            print("No new Block details") # TODO: Add count validation check, due to multiple prints
    
    # Add details provided by client to Blockchain
    def add_block_to_blockchain(self, new_block_dict):
        self.blockchain.addBlock(Block(new_block_dict))
        self.saveChain(self.blockchain)
        
        print("Added Block to Blockchain!")

        # Once Block successfully added to Blockchain, send Block Details to clients
        self.send_block_to_clients(new_block_dict)

    # Send new Block added to Blockchain to Client
    def send_block_to_clients(self, new_block):
        new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)
        new_block_doc.set(new_block)

        print("Sent Block to Clients! ") # TODO: Add count validation check, due to multiple prints

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

        # Ensure all clients have acknowledged before releasing callback
        if (curr_ack == self.clients_count):
            print("Clients ack-ed") # TODO: Add count validation check, due to multiple prints
            self.ack_callback_done.set()
            
            # Once all clients have acknowledged, remove block details
            new_block_doc = self.db.collection(BLOCK_COLL).document(NEW_BLOCK)
            new_block_doc.delete()

            self.ack_doc.update({'ack':0})

    def saveChain(self, bcObj, name="savedChain"):
        try:
            # Pickling the chain
            saveFile = open(SAVEDCHAIN, 'ab') # Use binary mode (Important)
            # Write object into file
            pickle.dump(bcObj, saveFile)                     
            saveFile.close()
            print("\n----- CHAIN SAVED -----")
        except:
            print("Error saving blockchain! Ensure save object is not None!")

    def loadChain(self, name="savedChain", printChain=False): # Load the default chain for demo and grading purposes
        try:
            saveFile = open(SAVEDCHAIN, 'rb') # TODO: Change the file path when using Docker Persistent Storage
            savedChain = pickle.load(saveFile)
            print("\n----- CHAIN LOADED -----")
            if (printChain):
                savedChain.printChain()
                print("The blockchain's validity is", savedChain.isValid())
                print("\n------------------------")
            return savedChain
        except:
            print("There is no local backup of the chain. If this seems wrong, it means local copy of the blockchain has been compromised!")

            backupCount = len(self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).collection('savedChain.bc').get())
            if backupCount > 0:
                print("Attempting to retrieve cloud backup of the chain...")
                self.requestBackup()
            else:
                print("Creating a new empty chain...")
                return Blockchain() # Return an empty blockchain temporarily. If no backup, blockchain is empty.

    def requestBackup(self):
        self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).set({})
        self.pollRequestResponse()

    # Check if a new user is added to system and requested for a copy of the blockchain
    def pollRequestResponse(self):
        # Create an Event for notifying main Thread
        self.blockchainReqCallbackDone = threading.Event()
        self.blockchainReqResDoc = self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).collection('savedChain.bc')
        
        # Watch the document for changes
        self.copyResponseDocWatch = self.blockchainReqResDoc.on_snapshot(self.onResponseSnapshot)
    
    # Callback function to capture changes to blockchain requests
    def onResponseSnapshot(self, coll_snapshot, changes, read_time):
        response_list = []

        try:
            for response in coll_snapshot: # For each document in a sub collection
                # print(requests.to_dict())
                response_list.append(response.to_dict()) 
            
            print("\nReceived new blockchain backup copy")
        except Exception as e:
            print("While handling reponse: ", e)

        if response_list:
            response_list.sort(key=lambda x:x['request_time']) # sort by earliest request time

            length = 0
            longestBC = None
            clientID = "Nobody" # Variable used for printing. Remove if no longer printing logs

            for entry in response_list: # Iterate through every backup entry
                bcBlob = entry.get('blockchain')
                bc = pickle.loads(bcBlob) # Unblobify the raw data to blockchain form

                if length == 0: # Base case
                    length = bc.chain.size()
                    longestBC = bc
                    clientID = entry.get('clientID')

                if bc.chain.size() > length: # If a blockchain is longer than current longest
                    length = bc.chain.size()
                    longestBC = bc
                    clientID = entry.get('clientID')

            print("Blockchain has been updated with cloud backup data from", clientID)
            print(longestBC.printChain())
            # Pickling the chain
            saveFile = open(SAVEDCHAIN, 'ab') # Use binary mode (Important)
            # Write object into file
            pickle.dump(longestBC, saveFile)                     
            saveFile.close()

            # Uncomment if backups need to be deleted by server (Increased Confidentiality & Integrity but reduced Availability)
            # for doc in coll_snapshot:
            #     self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).collection('savedChain.bc').document(doc.id).delete()
            # self.db.collection(BLOCK_COLL).document(BLOCKCHAIN_BACKUP).delete()

            self.blockchainReqCallbackDone.set() # Stop the thread




if __name__ == '__main__':
    bc_server()