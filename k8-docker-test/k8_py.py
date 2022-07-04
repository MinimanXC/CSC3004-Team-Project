from datetime import datetime
import time
import os

i=0
__file__ = "../app-data/test_file.txt"

while True:
    # datetime object containing current date and time
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")

    # Writing to file
    with open(__file__, "a+") as file1:
        # Writing data to a file
        file1.write("Hello \n")
        file1.write(str(dt_string))
        file1.write("\n")
    
    # Reading from file
    with open(__file__, "r+") as file1:
        # Reading form a file
        print(file1.read())

    # print("Path at terminal when executing this file")
    # print(os.getcwd() + "\n")

    # print("This file full path (following symlinks)")
    # full_path = os.path.realpath(__file__)
    # print(full_path + "\n")

    # print("This file directory only")
    # print(os.path.dirname(full_path))

    time.sleep(10)
