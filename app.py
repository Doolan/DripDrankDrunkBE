from flask import Flask, request
import requests
import json

import pymongo
# from pymongo import MongoClient
# from flask.ext.pymongo import PyMongo

app = Flask(__name__)
client = pymongo.MongoClient("mongodb://venerdm:Rose!@drankonline-shard-00-00-ofd8a.mongodb.net:27017,drankonline-shard-00-01-ofd8a.mongodb.net:27017,drankonline-shard-00-02-ofd8a.mongodb.net:27017/admin?ssl=true&replicaSet=DrankOnline-shard-0&authSource=admin")
db = client.drink

# app.config['MONGO_DBNAME'] = 
# app.config['MONGO_URI'] = 

@app.route('/')
def main():
    return 'Hello, world!'

# API endpoint for new user 
# TODO check if user with that email already exists
@app.route('/newUser', methods=['POST'])
def createAccount():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})

    data = request.get_json()

    userTable = db.user
    newUser = {'email' : data['email'], 'password' : data['password']}
    success = userTable.insert_one(userTable)
    # if success != 
    #     return jsonify({'failure' : 'data insertion failure'})
    return jsonify({'success' : 'successfully added new user'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)