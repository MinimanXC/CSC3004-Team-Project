from itertools import chain
from typing import Optional
from tools import calculateHash
from linkedlist import LinkedList
import pickle

GENESIS_HASH = '0' * 64 # Constant value of 64 zeros. Used by genesis block as base case

# Each node in the linked list/block in the blockchain
class Block:

    _blockId: int
    _hash: str
    _prevHash: str
    previous: Optional['Block']
    _data: Optional[dict] # Dictionary which includes timestamp, transaction data and wtv data that needs to be added
    _nonce: int

    # Old constructor (but might still be relevant depending on code structure)
    def __init__(self, previous=None, data=None, nonce=0, hash=None, prevHash=None) -> None:

        if previous is None:  # If genesis block, id will be 0
            self._blockId = 0
        else:  # Else block id will be previous block id + 1
            self._blockId = previous.getBlockID() + 1

        self._hash = hash
        self._prevHash = prevHash
        self._data = data
        self.previous = previous
        self._nonce = nonce

    # Always instantiate using this constructor unless you know what you're doing
    def __init__(self, data=None) -> None:

        self._hash = None
        self._prevHash = None
        self._blockId = 0
        self._data = data
        self.previous = None
        self._nonce = 0

    # Recursive function 
    def getPreviousHash(self) -> str:
        if self.previous is None: # Base case of recursive function. Genesis block has no previous hash thus default to constant value of 0
            self._prevHash = GENESIS_HASH
            return self._prevHash
        else:
            self._prevHash = self.previous.getHash()
            return self._prevHash

    # Function to calculate hash based on previous hash and current data. Do not call if validity of block needs to be checked
    def getHash(self) -> str:
        self._hash = calculateHash(self._blockId, self.getPreviousHash(), self._data, self._nonce)
        return self._hash

    # Returns only the hash string instead of recalculating the hash and returning the updated hash
    def getPreviousCalculatedHash(self) -> str:
        return self._prevHash

    # Returns only the previous hash string instead of recalculating the previous hash and returning the updated previous hash
    def getCalculatedHash(self) -> str:
        return self._hash

    # Function may be removed if adopting permissioned blockchain. Replace with cryptography keys for authentication of users(?)
    def mine(self, zeroCount) -> None:
        # While the first x values in the hash are not equal to x leading zeros
        while self.getHash()[:zeroCount] != '0' * zeroCount:
            self._nonce += 1 # Increment nonce. Nonce will be ever changing and rehashed in getHash() until conditions are satisfied

    def setBlockID(self, id) -> None:
        self._blockId = id

    def getBlockID(self) -> int:
        return self._blockId

    def setData(self, data) -> dict:
        self._data = data
        self.getHash()

    def getData(self) -> dict:
        return self._data

    def getNonce(self) -> int:
        return self._nonce

    def __str__(self) -> str:
        return str('\nBlock %s\nHash: %s\nPrevious Hash: %s\nData: %s\nNonce: %s' % (
            self._blockId,
            self._hash,
            self._prevHash,
            str(self._data),
            self._nonce)
        )

# Glorified LinkedList (Change my mind)
class Blockchain():

    def __init__(self, difficulty=4) -> None:
        self.difficulty = difficulty
        self.chain = LinkedList()
        self.addBlock(Block("This is the Genesis Block and the start of your transactions!"))

    def getDifficulty(self) -> int:
        return self.difficulty

    def addBlock(self, block: Block) -> None:
        if self.chain.size() == 0:
            #self.mineBlock(block)
            block.getHash()
            self.chain.insert(block)
        else:
            block.previous = self.chain.head.data
            block.setBlockID(block.previous.getBlockID() + 1)
            block.getHash()
            #self.mineBlock(block)
            self.chain.insert(block)

    # Do not call. Mining not needed in permissioned blockchain
    def mineBlock(self, block: Block) -> None:
        block.mine(self.difficulty) # Getting difficulty issues because im not updating the block id at this point in time

    def isValid(self) -> bool:
        # Temporarily convert reverse linked list to array to have an easier time iterating
        chainList = self.chain.toArray()

        for i in range(0, len(chainList) - 1): # Iterate through each block, ignoring the genesis block (the last element in the array)
            prevHashInBlock = chainList[i].getPreviousCalculatedHash()
            hashInPrevBlock = chainList[i + 1].getCalculatedHash()

            # Uncomment only if mining is needed again
            # if prevHashInBlock != hashInPrevBlock or hashInPrevBlock[:self.difficulty] != '0' * self.difficulty:
            #     return False

            if prevHashInBlock != hashInPrevBlock:
                return False

        return True

    def printChain(self) -> None:
        self.chain.printList()

    def getChain(self) -> list[object]:
        chainList = self.chain.toArray()
        return chainList

    # Function for demo purposes, to test and proof validity of chain. DO NOT CALL OTHERWISE!!!
    def breakChain(self, printChain=False):
        if self.chain.size() > 1: # Blockchain must have more than 1 block for validity to work
            self.chain.head.prev.data.setData("This block has been modified!")
            if printChain:
                self.printChain()
            
        

# if __name__ == '__main__':
#     # DIFFICULTY = 4 # Const var to enforce number of zeros in hash. Remove if no longer mining

#     # b0 = Block()
#     # b1 = Block(b0)
#     # b2 = Block(b1)
#     # b3 = Block(b2)

#     # # --- Optional if mining is not needed. Mining only enforces number of leading zeros for increased computation time ---
#     # b0.mine(DIFFICULTY)
#     # b1.mine(DIFFICULTY)
#     # b2.mine(DIFFICULTY)
#     # b3.mine(DIFFICULTY)
#     # # ---------------------------------------------------------------------------------------------------------------------

#     # print(b0)
#     # print(b1)
#     # print(b2)
#     # print(b3)
    
#     blockchain = Blockchain()
#     testData = ["Ligma", "Sugma", "Sawcon", "Kisma", "Dragon"]

#     for i in range(5):
#         blockchain.addBlock(Block(testData[i]))

#     blockchain.printChain()
#     print("The blockchain's validity is", blockchain.isValid())

#     # Pickling the chain
#     saveFile = open('savedChain.bc', 'ab') # Use binary mode (Important)
#     # Write object into file
#     pickle.dump(blockchain, saveFile)                     
#     saveFile.close()
#     print("\n----- CHAIN SAVED -----")

#     # Trying to invalidate the block to test validity function
    
#     blockchain.chain.head.prev.data.setData("Yo mama")
#     #blockchain.chain.head.prev.data.mine(0)
#     blockchain.printChain()
#     print("The blockchain's validity is", blockchain.isValid())

#     # Read in binary mode (Important)
#     saveFile = open('savedChain.bc', 'rb')     
#     savedChain = pickle.load(saveFile)
#     print("\n----- CHAIN LOADED -----")
#     savedChain.printChain()
#     print("The blockchain's validity is", savedChain.isValid())
#     print("\n------------------------")
#     saveFile.close()
