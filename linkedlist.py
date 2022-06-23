# Reverse Linked List to emulate a blockchain as most blockchain tutorials utilize an array

# Normal Linked List:
# [Head (Node A / Genesis)] -> [Node B] -> [Node C]

# Reversed Linked List:
# [Node A (Genesis)] <- [Node B] <- [Head (Node C)]

from numpy import array


class Node:
   def __init__(self, data=None) -> None:
      self.data = data
      self.prev = None

class LinkedList:
    def __init__(self):
      self.head = None

    def insert(self, data) -> None:
        newNode = Node(data)
        if self.head is None: # If there is no head node, means the new node is the first node
            newNode.prev = None # Therefore previous pointer will point to nothing
            self.head = newNode # And new node will be head node
        else:
            newNode.prev = self.head
            self.head = newNode

    def size(self) -> int:
        size = 0
        temp = self.head
        while temp is not None:
            size += 1
            temp = temp.prev
        return size

    def printList(self) -> None:
        if self.size() <= 0:
            print("The list is empty")
        else:
            temp = self.head
            print("\nThe blocks in the Chain are as follows:")
            print("\n[HEAD] (Most recent block)\n")
            while temp is not None:
                #print('\nBlock %s' % (str(temp.data.getBlockID())))
                print('Block %s\n' % (str(temp.data)))
                temp = temp.prev
            print("[TAIL] (Genesis Block)\n")

    # Returns the data in the LinkedList as an Array in reverse order. E.g: INPUT: LinkedList - [0, 1, 2, 3, 4] OUTPUT: Array - [4, 3, 2, 1, 0]
    def toArray(self) -> list[object]:
        if self.size() <= 0:
            print("The list is empty")
        else:
            temp = self.head
            tempArr = []
            while temp is not None:
                #tempArr.append(temp.data.getBlockID())
                tempArr.append(temp.data)
                temp = temp.prev
            return tempArr


if __name__ == '__main__':
    list = LinkedList()
    list.insert(0)
    list.insert(1)
    list.insert(2)
    list.insert(3)
    print("The linked list is of size: ", list.size())
    list.printList()


