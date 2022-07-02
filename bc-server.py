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
    import firebase_admin
    from firebase_admin import credentials, firestore

    print("Dependencies loaded successfully")
except:
    print("Failed to load dependencies")

class bc_server():

    def __init__(self):
        # Initialise Firebase SDK
        self.cred = credentials.Certificate("firebase-auth.json")
        firebase_admin.initialize_app(self.cred)
        # Initialize firestore instance
        self.firestore_db = firestore.client()

    def main(self):
        pass

    def request_lock(self):
        request_lock_coll = self.db.collection(BLOCK_COLL).document(REQUEST_LOCK).collections()
        # # docs = request_coll[0].stream().order_by(u'request_time')
        # for requests in request_lock_coll:
        #     docs = requests.stream()
        #     docs = docs.order_by(u'request_time')
        #     for doc in docs:
        #         print(f'{doc.id} => {doc.to_dict()}')    

if __name__ == '__main__':
    bc_server()