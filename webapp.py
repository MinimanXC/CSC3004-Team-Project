from flask import Flask, render_template
from blockchain import *

app = Flask(__name__)

@app.route('/')
def hello_world():
    blockchain = Blockchain()
    testData = ["Ligma", "Sugma", "Sawcon", "Kisma", "Dragon"]

    for i in range(5):
        blockchain.addBlock(Block(testData[i]))

    # blockchain.printChain()
    chainList = blockchain.getChain()


    return render_template('index.html', data=chainList[::-1])

if __name__ == '__main__':
	app.run(debug=True)