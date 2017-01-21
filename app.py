from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
import requests
import json
import bleach
import time
import datetime

import pymongo

app = Flask(__name__)
client = pymongo.MongoClient("mongodb://venerdm:Rose!2@drankonline-shard-00-00-ofd8a.mongodb.net:27017,drankonline-shard-00-01-ofd8a.mongodb.net:27017,drankonline-shard-00-02-ofd8a.mongodb.net:27017/admin?ssl=true&replicaSet=DrankOnline-shard-0&authSource=admin")
db = client.drink

app.debug = True
app.secret_key = 'secret'

jwt = JWTManager(app)

    
#time format stored as year,month,day,hour,minute
def emptyPersonObject():
    #using utc time for all timestamps. Can change later
    currentTime = time.time()
    person = {
        'dateofbirth' : '' ,
        'name' : '' ,
        'sex' : '', 
        'height' : '',
        'weight' : '',
        'registration' : currentTime
    }

    return person

def createNewNight():
    currentTime = time.time()
    night = {
        'date' : currentTime,
        'numberOfDrinks' : 0,
        'personID' : '',
        'drinkBreakdown' : []
    }

    return night

def getTonight(nightObjects, todayDate):
    for night in nightObjects:
        nightTime = datetime.datetime.utcfromtimestamp(int(night['data']))
        if nightTime.year == todayDate.year and nightTime.month == todayDate.month and nightTime.day == todayDate.day:
            return night
    return None


#TODO Update all database interactions to use transactions, so if some operation fails the entire thing aborts

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email  = bleach.clean(data['email'])
    password = bleach.clean(data['password'])
    user_table = db.user
    check = user_table.find_one({'email' : email})
    if check and check['password'] == password:
        ret = {'access_token' : create_access_token(identity=email)}
        return jsonify(ret), 200
    else:
        return jsonify({'failure' : 'Failed to Login'}), 401

@app.route('/')
def main():
    return 'Hello, world!'

#TODO implement password hashing
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
    
    ret = {'access_token' : create_access_token(identity=newUserEmail)}
    return jsonify(ret), 200

@app.route('/setUserData', methods=['POST'])
@jwt_required
def setUserData():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})
    
    #some setup
    fieldsTracked = ['dateofbirth', 'name', 'sex', 'height', 'weight']
    data = request.get_json()

    userTable = db.user
    personTable = db.person

    #grab email from the sent data and get the personID associated with this email
#    if 'email' not in data.keys():
#        return jsonify({'failure' : 'user\'s email was not included with this request'})

#    userEmail = bleach.clean(data['email'])
    userEmail = get_jwt_identity()
    userObject = userTable.find_one({'email' : userEmail})
    personID = userObject['personID']

    #now use the person object to update all of the fields that were sent
    for key in data.keys():
        if key in fieldsTracked:
            result = personTable.find_one_and_update({'_id' : personID}, {'$set': {key : bleach.clean(data[key])}})
            
            if result is None:
                return jsonify({'failure' : 'data update failure'})
        
    return jsonify({'success' : 'successfully updated person data'})  

# adds a new night to db, or updates if already in db
# night has personID, date, # of drinks, breakdown of drinks
# can only set data regarding the current day's night 
# assuming drinks are valid input
# TODO do data validation
@app.route('/setNight', methods=['POST'])
@jwt_required
def setNight():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})

    # init database tables
    nightTable = db.night
    userTable = db.user

    # get user data - personID is one part of the data that can uniquely identify a night
    data = request.get_json()
    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']

    # get current time and all night objects associated with a personID. Then uses that data to match a night with today's night if it exists
    currentTime = datetime.datetime.utcnow()
    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects, currentTime)
    if tonight == None:
        tonight = createNewNight()
        nightId = nightTable.insert_one(tonight)
    else:
        nightId = tonight['_id']

    #now add the new drinks to our night and update it in the database
    newDrinkType = data['drink']
    newDrinkTime = time.time()
    tonight['numberOfDrinks'] += 1
    tonight['drinks'].append({'drinkType' : newDrink, 'drinkTime' : newDrinkTime})

    nightTable.find_one_and_update({'_id' : nightId}, {'$set' : tonight})

    return jsonify({'success' : 'successfully updated night data'})  


#TODO figure out what to do when no start date is passed
@app.route('/getWeekData', methods=['POST'])
@jwt_required
def getWeekData():
    if request.method != 'POST':
        return jsonify({'failure' : 'incorrect request format'})

    data = request.get_json()

    userTable = db.user
    nightTable = db.night
    email = get_jwt_identity()


@app.route('/jwt_testing')
@jwt_required
def jwt_testing():
    email = get_jwt_identity()
    return jsonify({"success" : user}),200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
