from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_cors import CORS, cross_origin
import requests
import json
import bleach
import time
import datetime
import hashlib
from math import ceil
from twilio.rest import TwilioRestClient

import pymongo

app = Flask(__name__)
CORS(app)
client = pymongo.MongoClient("mongodb://venerdm:Rose!2@drankonline-shard-00-00-ofd8a.mongodb.net:27017,drankonline-shard-00-01-ofd8a.mongodb.net:27017,drankonline-shard-00-02-ofd8a.mongodb.net:27017/admin?ssl=true&replicaSet=DrankOnline-shard-0&authSource=admin")
db = client.drink


app.debug = True
app.secret_key = 'secret'

account = 'AC2c47cf85a53d0a61e129d2a27497cd61'
token = 'fadff4670cdae887fa72064ba3db6ee1'
client = TwilioRestClient(account,token)

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
        'weekAverage' : [0,0,0,0,0,0,0],
        'registration' : currentTime
    }

    return person

#rounds the current date down to the most recent noon + 1 minute
#takes in a datetime object to normalize
def normalizeDateTime(dt):
    dayChange = 0
    if dt.hour <= 12 and not (dt.hour == 12 and dt.minute > 0):
        dayChange = 1
    return (dt - datetime.timedelta(days=dayChange, hours=dt.hour, minutes=dt.minute))  + datetime.timedelta(hours=12,minutes=1)


def createNewNight():
    newStartDT = normalizeDateTime(datetime.datetime.utcnow())
    newEndDT = (newStartDT + datetime.timedelta(hours=23, minutes=59))

    newStartTimestamp = newStartDT.timestamp() 
    newEndTimestamp = newEndDT.timestamp()

    night = {
        'dateStart' : newStartTimestamp,
        'dateEnd' : newEndTimestamp,
        'numberOfDrinks' : 0,
        'personID' : '',
        'drinkBreakdown' : [],
        'dd_number' : ''
    }

    return night

def getTonight(nightObjects):
    currentTime = time.time()
    for night in nightObjects:
        if currentTime >= night['dateStart'] and currentTime <= night['dateEnd']:
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

@app.route('/getBio', methods=['GET'])
@jwt_required
def getBio():
    userTable = db.user
    personTable = db.person

    email = get_jwt_identity()
    user = userTable.find_one({'email' : email})

    personID = user['personID']
    person = personTable.find_one({'_id' : personID})
    
    height = person['height']
    sex = person['sex']
    weight = person['weight']

    return jsonify({'height' : height,'sex' : sex,'weight' : weight}), 200

@app.route('/needDD',methods=['GET'])
@cross_origin()
@jwt_required
def needDD():
    nightTable = db.night
    userTable = db.user
    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']

    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects)

    return jsonify({"need" : 'dd_name' in tonight.keys()})

@app.route('/getTonight',methods=['GET'])
@cross_origin()
@jwt_required
def getTonightResponse():
    nightTable = db.night
    userTable = db.user
    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']

    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects)

    return jsonify(tonight)




@app.route('/setDD',methods=['POST'])
@cross_origin()
@jwt_required
def addDD():
    nightTable = db.night
    userTable = db.user

    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']

    data = request.get_json()

    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects)

    tonight['dd_name'] = data['dd_name']
    tonight['dd_number'] = data['dd_number']

    nightTable.find_one_and_update({'_id' : nightId}, {'$set' : tonight})
    return jsonify({"succeeded" : 'woo'})

# adds a new night to db, or updates if already in db
# night has personID, date, # of drinks, breakdown of drinks
# can only set data regarding the current day's night 
# assuming drinks are valid input
# TODO do data validation
@app.route('/setNight', methods=['POST'])
@cross_origin()
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
    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects)
    first = False
    if tonight == None:
        tonight = createNewNight()
        tonight['personID'] = personID
        nightId = nightTable.insert_one(tonight).inserted_id
        first = True
    else:
        nightId = tonight['_id']

    #now add the new drinks to our night and update it in the database
    newDrinkType = data['drink']
    newDrinkTime = time.time()
    tonight['numberOfDrinks'] += 1
    if 'dd_number' in data.keys():
        tonight['dd_name'] = data['dd_name']
        tonight['dd_number'] = data['dd_number']
    tonight['drinkBreakdown'].append({'drinkType' : newDrinkType, 'drinkTime' : newDrinkTime})

    nightTable.find_one_and_update({'_id' : nightId}, {'$set' : tonight})

    return jsonify({'first' : first})  

@app.route('/batch',methods=['POST'])
def batch():
    nightTable = db.night
    personTable = db.person
    people = personTable.find()

    for person in people:
        nights = nightTable.find({'personID' : person['_id']})
        values = [0 for x in range(7)]
        minDate = 10000000000000
        maxDate = 0
        for night in nights:
            minDate = min(minDate,night['dateStart'])
            maxDate = max(maxDate,night['dateStart'])
            day = datetime.datetime.utcfromtimestamp(night['dateStart']).weekday()
            values[day]+=night['numberOfDrinks']
        weeks = max(1,ceil((maxDate-minDate)/(7*24*60*60)))
        person['weekAverage'] = [value/weeks for value in values]
        personTable.find_one_and_update({'_id' : person['_id']}, {'$set' : person})

    return jsonify({'success' : 'succesfully ran batch job'})
            

    
@app.route('/textDD', methods=['POST'])
@jwt_required
def text_dd():
    nightTable = db.night
    personTable = db.person
    userTable = db.user
    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']
    person = personTable.find_one({'_id' : personID})
    name = person['name']
    allNightObjects = nightTable.find({'personID' : personID})
    tonight = getTonight(allNightObjects)
    if tonight == None or 'dd_number' not in tonight.keys():
        return jsonify({'failure' : 'unable to text dd'})
    dd_number = tonight['dd_number']
    dd_name = tonight['dd_name']
    message = client.messages.create(to=dd_number, from_='+12816728234',body=dd_name +', your Friend ' + name+ ' is drunk, please keep an eye on them and make sure they get home safe!')
    return jsonify({'success' : 'dd texted'})



#if start date not sent use previous sunday
#start dates will always be sunday
# start dates will be sent as year,month,day in parameter timestring
@app.route('/getWeekData', methods=['GET'])
@jwt_required
def getWeekData():

    data = request.get_json()
    userTable = db.user
    personTable = db.person
    nightTable = db.night

    email = get_jwt_identity()
    userObject = userTable.find_one({'email' : email})
    personID = userObject['personID']

    # if a start date was not passed in we find the most recent sunday and send states for nights until today
    #assume date is passed in the form year,month,day
    dayNumber = datetime.datetime.today().weekday() + 1
    currentDT = datetime.datetime.utcnow()

    #if it is before noon we will roll back to previous day anyways so no need for the modifier
    if currentDT.hour < 12 or (currentDT.hour == 12 and currentDT.minute == 0):
        dayNumber -= 1

    if not 'startDate' in data.keys():
        startDate = normalizeDateTime(datetime.datetime.today() - datetime.timedelta(days=dayNumber))

    else:
        timestring = data['startDate']
        timearray = timestring.split(',')
        startDate = datetime.datetime(int(timearray[0]), int(timearray[1]), int(timearray[2]), 12, 1, 0)
        dayNumber = 7

    #loop through the amount of days we rolled backed, query for the data, and return it
    #this is n^2 when it could be n but whatever
    allNightObjects = nightTable.find({'personID' : personID})
    allNightObjects = [x for x in allNightObjects]
    currentDate = startDate
    weeklyDrinks = []
    breakdown = {'wine' : 0, 'liquor' : 0, 'beer' : 0, 'mixed' : 0, 'shot' : 0}
    totalDrinks = 0
    for i in range(0, dayNumber):
        currentDate = startDate + datetime.timedelta(days=i)
        currentTS = currentDate.timestamp()
        weeklyDrinks.append(0)
        for night in allNightObjects:
            if night['dateStart'] <= currentTS and night['dateEnd'] > currentTS:
                weeklyDrinks[i] = night['numberOfDrinks']
                totalDrinks += night['numberOfDrinks']
                for drink in night['drinkBreakdown']:
                    breakdown[drink['drinkType']] += 1
                break

    
    personObject = personTable.find_one({'_id' : personID})
    weekAverage = personObject['weekAverage']

    weekData = {'drinks' : weeklyDrinks, 'breakdown' : breakdown}
    weekAverage = {'drinks' : weekAverage}

    return jsonify({'weekData' : weekData, 'weekAverage' : weekAverage})
    

# @app.route('/jwt_testing')
# @jwt_required
# def jwt_testing():
#     email = get_jwt_identity()
#     return jsonify({"success" : user}),200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
