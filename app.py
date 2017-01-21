from flask import Flask, request, jsonify
import requests
import json
import bleach
import datetime

import pymongo
# from pymongo import MongoClient
# from flask.ext.pymongo import PyMongo

app = Flask(__name__)
client = pymongo.MongoClient("mongodb://venerdm:Rose!2@drankonline-shard-00-00-ofd8a.mongodb.net:27017,drankonline-shard-00-01-ofd8a.mongodb.net:27017,drankonline-shard-00-02-ofd8a.mongodb.net:27017/admin?ssl=true&replicaSet=DrankOnline-shard-0&authSource=admin")
db = client.drink

#time format stored as year,month,day,hour,minute
def emptyPersonObject():
    #using utc time for all timestamps. Can change later
    currentTime = datetime.datetime.utcnow()
    dtString = '%s,%s,%s,%s,%s' % (currentTime.year, currentTime.month, currentTime.day, currentTime.hour, currentTime.minute)
    person = {
        'dateofbirth' : '' ,
        'name' : '' ,
        'sex' : '', 
        'height' : '',
        'weight' : '',
        'registration' : dtString
    }

    return person

@app.route('/')
def main():
    return 'Hello, world!'

# API endpoint for creating a new user 
@app.route('/newUser', methods=['POST'])
def createAccount():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})

    # get data from user. Make sure you sanitize your inputs
    data = request.get_json()
    newUserEmail = bleach.clean(data['email'])
    newUserPassword = bleach.clean(data['password'])

    #connect to user table
    userTable = db.user
    personTable = db.person

    #checking to make sure 
    if userTable.find_one({'email' : newUserEmail}) != None:
        return jsonify({'failure' : 'user already exists'})

    # create a new person to associate with our new user
    newPerson = emptyPersonObject()
    result = personTable.insert_one(newPerson)

    newUser = {'email' : newUserEmail, 'password' : newUserPassword, 'personID' : result.inserted_id}
    result = userTable.insert_one(newUser)
    if not result.acknowledged:
        return jsonify({'failure' : 'data insertion failure'})
    
    return jsonify({'success' : 'successfully added new user'})

# @app.rought('/setUserData', methods=['POST'])
# def setUserData():
#     if request.method != 'POST':
#         return jsonify({'failure' : 'incorrect request format'})
    
#     fieldsTracked = ['age', 'name', 'sex', 'height', 'weight']

#     data = request.get_json()
#     keyList = []

#     #iterate through the JSON that was passed, do a sanity check on the keys, and then insert the data
#     for key in data.keys():
#         if key in fieldsTracked:
#             keyList.append(key)
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)