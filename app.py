from flask import Flask
from flask import jsonify, request
from crypt import methods
import pymongo
from pymongo import MongoClient
from bson.json_util import dumps
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from dateutil import parser
import random
import pandas as pd

app = Flask(__name__)

if __name__ == "__main__":
    app.run(debug=True)

try:
    # mongo = MongoClient('host.docker.internal', 27017)
    mongo = MongoClient('localhost', 27017)
    db = mongo.testflask

    mongo.server_info()  # Triggers exception if it cant conenct to DB

    db.list_collection_names()

    print("Database is connected!")

except:
    print("Error while connecting to DB")


@app.route("/user/<username>/", methods=["GET"])
def findUser(username):
    if username:
        resp = db.users.find_one({"username": username})
        if resp is not None:
            response = list()
            response.append({"username": resp["username"], "email": resp["email"], "password": resp["password"]})

        return jsonify(response)
    else:
        not_found()


@app.route("/users", methods=["GET"])
def findUsers():
    holder = list()
    for i in db.users.find():
        holder.append({"username": i["username"], "email": i["email"], "password": i["password"]})
    return jsonify(holder)


@app.route('/users/add', methods=['POST'])
def add():
    _json = request.json
    _name = _json['username']
    _email = _json['email']
    _password = _json['password']

    if _name and _email and _password and request.method == 'POST':
        users = db.users
        _hashedpwd = generate_password_hash(_password)

        id = users.insert_one({'username': _name, 'email': _email, 'password': _hashedpwd})

        resp = jsonify("User added succesfully")

        resp.status_code = 201

        return resp
    else:
        return not_found()


@app.route('/user/<username>/delete', methods=['DELETE'])
def deleteUser(username):
    db.users.delete_one({"username": username})

    return jsonify("User deleted succesfully")


@app.route('/user/<username>/update', methods=['PUT'])
def updateUser(username):
    _username = request.json['username']
    _email = request.json['email']

    if _username and not _email:
        updatedUser = db.users.update_one({'username': _username})

    if not _username and _email:
        updatedUser = db.users.update_one({'email': _email})

    if _username and _email:
        updatedUser = db.users.update_one({'username': username}, {"$set": {'username': _username, 'email': _email}})

    return jsonify("User Updated")

@app.route('/user/<username>/tracker', methods=['POST', 'GET'])
def track(username):
    if request.method == 'POST':
        _username = username
        _days = list()
        input_days = request.json['days']
        for day in input_days:
            date_time_str = day["date"]
            print(date_time_str)
            date_time_obj = datetime.strptime(date_time_str, '%d/%m/%y')
            _days.append({"day": date_time_obj, "present": day["present"]})

        db.attendance.insert_one({'user': _username, 'attendance': _days})
        return jsonify("Added dates to tracking")

    if request.method == 'GET':
        _username = username
        resp = db.attendance.find_one({"user": _username})
        if resp is not None:
            response = list()
            response.append({"username": resp["user"], "days": resp["attendance"]})
            return jsonify(response)
        else:
            return jsonify("Error loading user")

@app.route("/user/<username>/tracker/<day>", methods=['GET'])
def getStats(username, day):
    if request.method != 'GET':
        return jsonify("Response empty")
    _username = username
    _day = day
    resp = db.attendance.find_one({"user": _username})
    if resp is None:
        return jsonify("Response empty")

    response = list()
    _days = resp["attendance"]
    _office_cnt = 0
    _home_cnt = 0
    _weekend_cnt = 0
    _absent_cnt = 0
    for _weekday in _days:
        weekday = _weekday.get("day")
        if weekday.strftime('%A').lower() == day:
            response.append({"day": weekday, "present": _weekday.get("present")})
            if _weekday.get("present") == "office":
                _office_cnt += 1
            elif _weekday.get("present") == "home":
                _home_cnt += 1
            elif _weekday.get("present") == "absent":
                _absent_cnt += 1
            else:
                _weekend_cnt += 1
    percentageResponse = list()
    officePerc = (_office_cnt / len(response)) * 100
    homePerc = (_home_cnt / len(response)) * 100
    absentPerc = (_absent_cnt / len(response)) * 100
    weekendPerc = (_weekend_cnt / len(response)) * 100

    return jsonify({"Office": officePerc, "Home": homePerc, "Absent": absentPerc, "Weekend": weekendPerc})

@app.route("/user/<username>/tracker/<day>/meetings", methods=['GET'])
def getBusyPercentage(username, day):
    _hour = request.json["hour"]

    calendarColl = db.calendar.find({"user": username})
    if calendarColl is None:
        return jsonify("Calendar is empty for this user")
    _record = list()
    _meetingCnt = 0
    _dayCnt = 0
    for record in calendarColl:
        _record.append({"start": record["record"].get("start"), "end": record["record"].get("end")})
        _startTime = parser.parse(record["record"].get("start").get("dateTime"))
        _endTime = parser.parse(record["record"].get("end").get("dateTime"))
        _day = _startTime.strftime('%A').lower()
        if day == _day:
            _dayCnt += 1
            if _hour >= _startTime.hour and _hour <= _endTime.hour and day == _day:
                _meetingCnt += 1

    _meetPerc = (_meetingCnt / _dayCnt) * 100

    return jsonify({"Meeting percentage": _meetPerc, "Number of days": _dayCnt, "Meetings": _meetingCnt})

@app.route('/populate/attendance', methods=['GET'])
def populateAttendance():
    days = pd.date_range(end = datetime.today(), periods=276).to_pydatetime().tolist()
    _attendance = list()
    for day in days:
        _present = random.randint(1, 3)
        _presencestr = ""
        if _present == 1:
            _presencestr = "office"
        elif _present == 2:
            _presencestr = "home"
        elif _present == 3:
            _presencestr = "absent"
        _attendance.append({"day": day, "present": _presencestr})

    db.attendance.insert_one({"user": "fulluser", "attendance": _attendance})
    return jsonify("User attendance imported")

@app.route('/populate/calendar', methods=['GET'])
def populateCalendar():
    _user = "fulluser"
    _subject = "Testing Subject Mass Input"
    _timezone = "UTC"
    for i in range(0, 200):
        _hours = random.randint(0, 21)
        _day = random.randint(1, 28)
        _month = random.randint(1, 9)

        _startdate = datetime(2022, _month, _day, _hours, 0, 0, 0, None)
        _enddate = datetime(2022, _month, _day, _hours + 2, 0, 0, 0, None)


        db.calendar.insert_one({"user": _user, "subject": _subject, "record": {"start": {"dateTime": _startdate.isoformat(), "timeZone": _timezone}, "end": {"dateTime": _enddate.isoformat(), "timeZone": _timezone}}})

    return jsonify("Calendar has been populated")

@app.errorhandler(404)
def not_found(error=None):
    message = {
        'status_code': 404,
        'message': 'Not Found' + request.url
    }

    resp = jsonify(message)

    resp.status_code = 404

    return resp