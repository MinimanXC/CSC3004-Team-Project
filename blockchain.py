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

    # Old constructor (but might still be relevant depending on code structure)
    def __init__(self, previous=None, data=None, hash=None, prevHash=None) -> None:

        if previous is None:  # If genesis block, id will be 0
            self._blockId = 0
        else:  # Else block id will be previous block id + 1
            self._blockId = previous.getBlockID() + 1

        self._hash = hash
        self._prevHash = prevHash
        self._data = data
        self.previous = previous

    # Always instantiate using this constructor unless you know what you're doing
    def __init__(self, data=None) -> None:

        self._hash = None
        self._prevHash = None
        self._blockId = 0
        self._data = data
        self.previous = None

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
        self._hash = calculateHash(self._blockId, self.getPreviousHash(), self._data)
        return self._hash

    # Returns only the hash string instead of recalculating the hash and returning the updated hash
    def getPreviousCalculatedHash(self) -> str:
        return self._prevHash

    # Returns only the previous hash string instead of recalculating the previous hash and returning the updated previous hash
    def getCalculatedHash(self) -> str:
        return self._hash

    # Function may be removed if adopting permissioned blockchain. Replace with cryptography keys for authentication of users(?)
    def mine(self, zeroCount) -> None:
        pass
        # While the first x values in the hash are not equal to x leading zeros
        #while self.getHash()[:zeroCount] != '0' * zeroCount:
            #self._nonce += 1 # Increment nonce. Nonce will be ever changing and rehashed in getHash() until conditions are satisfied

    def setBlockID(self, id) -> None:
        self._blockId = id
        self.getHash()

    def getBlockID(self) -> int:
        return self._blockId

    def setData(self, data) -> dict:
        self._data = data
        self.getHash()

    def getData(self) -> dict:
        return self._data

    # def getNonce(self) -> int:
    #     return self._nonce

    def __str__(self) -> str:
        return str('\nBlock %s\nHash: %s\nPrevious Hash: %s\nData: %s' % (
            self._blockId,
            self._hash,
            self._prevHash,
            str(self._data))
            #self._nonce)
        )

# Glorified LinkedList (Change my mind)
class Blockchain():

    def __init__(self, difficulty=4) -> None:
        self.tamperedCount = -1 # Init as -1 as 0 is Genesis Block
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
            #block.getHash() # No need to call this cause setBlockID() has been refactored to call it instead to increase security
            #self.mineBlock(block)
            self.chain.insert(block)

    # Do not call. Mining not needed in permissioned blockchain
    def mineBlock(self, block: Block) -> None:
        block.mine(self.difficulty) # Getting difficulty issues because im not updating the block id at this point in time

    def isValid(self) -> bool:
        # If no blocks or only genesis block, chain will always be valid
        if self.chain.size() <= 1:
            return True
        else:
            temp = self.chain.head # Head will always be most recent block. Tail will always be genesis

            while temp is not None:
                prevHashInBlock = temp.data.getPreviousCalculatedHash()
                if temp.prev is not None:
                    hashInPrevBlock = temp.prev.data.getCalculatedHash()
                else:
                    hashInPrevBlock = GENESIS_HASH

                if prevHashInBlock != hashInPrevBlock:
                    if temp.prev is not None:
                        self.tamperedCount = temp.prev.data.getBlockID()
                        print("Block", self.tamperedCount, "has been tampered with!")
                    else: # This else statement is a 'just in case' condition and most likely won't ever trigger
                        self.tamperedCount = 0
                        print("The genesis hash of the Genesis Block has been tampered with!")
                    return False

                temp = temp.prev # Line to iterate through the LL. Treat as i++

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

# Uncomment and run to test only the blockchain portion of the code
# if __name__ == '__main__':
#     blockchain = Blockchain()
#     testData = ["Ligma", "Sugma", "Sawcon", "Kisma", "Dragon"]
#     for i in range(5):
#         blockchain.addBlock(Block(testData[i]))
#     blockchain.printChain()
#     print("The blockchain's validity is", blockchain.isValid())

#     blockchain.breakChain(True)
#     print("The blockchain's validity is", blockchain.isValid())