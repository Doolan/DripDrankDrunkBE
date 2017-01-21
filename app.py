from flask import Flask, request, jsonify
import requests
import json
import bleach
import datetime

import pymongo

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

#TODO Update all database interactions to use transactions, so if some operation fails the entire thing aborts

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
    if not result.acknowledged:
        return jsonify({'failure' : 'data insertion failure'})

    newUser = {'email' : newUserEmail, 'password' : newUserPassword, 'personID' : result.inserted_id}
    result = userTable.insert_one(newUser)
    if not result.acknowledged:
        return jsonify({'failure' : 'data insertion failure'})
    
    #TODO update this to also return the json token 
    return jsonify({'success' : 'successfully added new user'})

@app.rought('/setUserData', methods=['POST'])
def setUserData():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})
    
    #some setup
    fieldsTracked = ['age', 'name', 'sex', 'height', 'weight']
    data = request.get_json()

    userTable = db.user
    personTable = db.person

    #TODO update this to grab json token from request header
    #grab email from the sent data and get the personID associated with this email
    if 'email' not in data.keys():
        return jsonify({'failure' : 'user\'s email was not included with this request'})

    userEmail = bleach.clean(data['email'])
    userObject = userTable.find_one({'email' : userEmail})
    personID = userObject['personID']

    #now use the person object to update all of the fields that were sent
    for key in data.keys():
        if key in fieldsTracked:
            result = personTable.find_one_and_update({'_id' : personID}, {'$set':{key : bleach.clean(data[key])}})
            
            if not result.acknowledged:
                return jsonify({'failure' : 'data update failure'})
        
    return jsonify({'success' : 'successfully added new user'})    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)