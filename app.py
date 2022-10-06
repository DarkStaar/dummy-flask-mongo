import uuid
import requests
from flask import Flask, render_template, session, request, redirect, url_for, jsonify
from flask_session import Session  # https://pythonhosted.org/Flask-Session
import msal
import app_config
from datetime import datetime
from dateutil import parser
import random
import pandas as pd
from pymongo import MongoClient
from dotenv import dotenv_values
from flask_crontab import Crontab

app = Flask(__name__)
app.config.from_object(app_config)
Session(app)

crontab = Crontab(app)

config = dotenv_values(".env")

#Global token variable used for API calls that need Application Token
app_token_global = ""

# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

try:
    # mongo = MongoClient('host.docker.internal', 27017)
    mongo = MongoClient('host.docker.internal', 27017)
    db = mongo.testflask

    mongo.server_info()  # Triggers exception if it cant conenct to DB

    print("Database is connected!")

except:
    print("Error while connecting to DB")

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template('index.html', user=session["user"], version=msal.__version__)

@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html", auth_url=session["flow"]["auth_uri"], version=msal.__version__)

@app.route(app_config.REDIRECT_PATH)  # Its absolute URL must match your app's redirect_uri set in AAD
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))

# Keep commented until API permissions for Application are allowed
# @crontab.job(minute="0",hour="22")
# def scheduled_job():

def getToken():
    global app_token_global

    token = requests.post(app_config.AZURE_TOKEN_URL, headers={'Content-Type': 'application/x-www-form-urlencoded'}, data=f"client_id={app_config.CLIENT_ID}&resource=https://graph.microsoft.com&client_secret={app_config.CLIENT_SECRET}&grant_type=client_credentials",).json()

    app_token_global = token["access_token"]

    return token["access_token"]

def getUserToken():
    global user_token_global
    #TODO 2FA doesnt allow to get User Access Token
    token = requests.post(app_config.AZURE_TOKEN_URL, data=f'grant_type=password&client_id={app_config.CLIENT_ID}&client_secret={app_config.CLIENT_SECRET}&resource=https://graph.microsoft.com&userName={app_config.USERNAME}&password={app_config.PASSWORD}',).json()

    print(token)

    user_token_global = token["access_token"]

    return token["access_token"]

def getusers():
    getToken()
    global app_token_global

    users = requests.get(app_config.ENDPOINT1, headers={'Authorization': 'Bearer ' + app_token_global}).json()

    return users.get("value")

def get_groups():
    getToken()
    global app_token_global

    groups = requests.get(app_config.ENDPOINT_GROUPS, headers={'Authorization': 'Bearer ' + app_token_global}).json()

    return groups.get("value")
def get_users_presence():
    getUserToken()
    global app_token_global

    _users = db.users.find({})
    _userlist = list()

    for user in _users:
        _userId = user.get("id")

        res = requests.get(f'https://graph.microsoft.com/beta/users/{_userId}/presence', headers={'Authorization': 'Bearer ' + app_token_global}).json()

        _outOffice = res.get("outOfOfficeSettings").get("isOutOfOffice")
        _message = res.get("outOfOfficeSettings").get("message")
        _presence = ""
        if _outOffice is True and _message != "home":
            _presence = "home"
        elif _outOffice is True:
            _presence = "absent"
        else:
            _presence = "office"

        _userlist.append({'id': _userId, 'presence': _presence})

    return _userlist

@app.route('/user/<userId>/tracker', methods=['POST', 'GET'])
def track(userId):
    if request.method == 'POST':
        _userId = userId
        _days = list()

        input_days = request.json['days']

        resp = db.attendance.find_one({"id": _userId})
        _days = resp["attendance"]
        for day in input_days:
            date_time_str = day["date"]

            date_time_obj = datetime.strptime(date_time_str, '%d/%m/%y')
            _days.append({"day": date_time_obj, "present": day["present"]})

        db.attendance.delete_one({'id': _userId})
        db.attendance.insert_one({'id': _userId, 'attendance': _days})
        return jsonify("Added dates to tracking")

    if request.method == 'GET':

        _userId = userId
        resp = db.attendance.find_one({"id": _userId})
        if resp is not None:
            response = list()
            response.append({"userId": resp["id"], "days": resp["attendance"]})
            return jsonify(response)
        else:
            return jsonify("Error loading user")

@app.route("/user/<userId>/tracker/<day>", methods=['GET'])
def getStats(userId, day):
    if request.method != 'GET':
        return jsonify("Response empty")
    _userId = userId
    _day = day
    resp = db.attendance.find_one({"id": _userId})
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

    officePerc = (_office_cnt / len(response)) * 100
    homePerc = (_home_cnt / len(response)) * 100
    absentPerc = (_absent_cnt / len(response)) * 100
    weekendPerc = (_weekend_cnt / len(response)) * 100

    return jsonify({"Office": officePerc, "Home": homePerc, "Absent": absentPerc, "Weekend": weekendPerc})

@app.route("/user/<userId>/tracker/<day>/meetings", methods=['GET'])
def getBusyPercentage(userId, day):
    _hour = request.json["hour"]

    calendarColl = db.calendar.find_one({"id": userId})
    calCol = calendarColl["days"]
    if calendarColl is None:
        return jsonify("Calendar is empty for this user")
    _record = list()
    _meetingCnt = 0
    _dayCnt = 0
    if day.lower() == 'saturday' or day.lower() == 'sunday':
        return jsonify("Weekend")

    for record in calCol:
        _starting = record.get("Meetings").get("start")
        _ending = record.get("Meetings").get("end")

        _record.append({"start": record.get("Meetings").get("start"), "end": record.get("Meetings").get("end")})
        if _starting is None or _ending is None:
            _day = record.get("day").strftime('%A').lower()
            if day == _day:
                _dayCnt += 1

        else:
            _startTime = parser.parse(record.get("Meetings").get("start"))
            _endTime = parser.parse(record.get("Meetings").get("end"))
            _day = _startTime.strftime('%A').lower()
        if day == _day:
            _dayCnt += 1
            if _hour >= _startTime.hour and _hour <= _endTime.hour and day == _day:
                _meetingCnt += 1

    _meetPerc = (_meetingCnt / _dayCnt) * 100

    return jsonify({"Meeting percentage": _meetPerc, "Number of days": _dayCnt, "Meetings": _meetingCnt})
@app.route('/populate/attendance', methods=['GET'])
def populateAttendance():
    days = pd.date_range(start= datetime(2022, 1, 1), end = datetime.today()).to_pydatetime().tolist()
    _attendance = list()
    _userslist = get_users_presence()
    for user in _userslist:
        for day in days:
            _presencestr = user.get("presence")
            if day.strftime('%A').lower() == 'saturday':
                _presencestr = "weekend"
            if day.strftime('%A').lower() == 'sunday':
                _presencestr = "weekend"
            _attendance.append({"day": day, "present": _presencestr})

        db.attendance.insert_one({"id": user.get("id"), "attendance": _attendance})
    return jsonify("User attendance imported")


@app.route('/populate/calendar', methods=['GET'])
def populateCalendar():
    _userId = ""
    _subject = "Testing Subject Mass Input"
    _meetings = list()
    _attendanceUsers = db.attendance.find({})

    days = pd.date_range(start=datetime(2022, 1, 1, 1, 1), end=datetime.today()).to_pydatetime().tolist()

    for user in _attendanceUsers:
        _userId = user.get("id")
        for i in days:
            _hours = random.randint(8, 16)

            _startdate = datetime(i.year, i.month, i.day, _hours, 0, 0, 0, None)
            _enddate = datetime(i.year, i.month, i.day, _hours + 2, 0, 0, 0, None)

            if _startdate.strftime('%A').lower() != 'sunday' and _startdate.strftime('%A').lower() != 'saturday':
                _meetings.append({"day": i, "Meetings": {"subject": _subject, "start": _startdate.isoformat(), "end": _enddate.isoformat()}})
            else:
                _meetings.append({"day": i, "Meetings": {"subject": "Weekend"}})

        db.calendar.insert_one({"id": _userId, "days": _meetings})

    return jsonify("Calendar has been populated")

@app.route('/populate/users', methods=['GET'])
def populate_users():
    _userarr = getusers()

    for user in _userarr:
        _displayName = user.get("displayName")
        _id = user.get("id")
        _workmail = user.get("userPrincipalName")
        _jobTitle = user.get("jobTitle")
        _officeLocation = user.get("officeLocation")

        db.users.insert_one({"id": _id, "displayName": _displayName, "workMail": _workmail, "jobTitle": _jobTitle, "officeLocation": _officeLocation})

    return jsonify("User collection has been populated!")

@app.route('/populate/groups', methods=['GET'])
def populate_groups():
    _groupsarr = get_groups()

    getToken()
    global app_token_global

    for group in _groupsarr:
        _groupId = group.get("id")
        _groupDescription = group.get("description")
        _displayName = group.get("displayName")
        _groupMail = group.get("mail")

        relationship = requests.get(app_config.ENDPOINT_GROUPS + f'/{_groupId}/members?$count=true', headers={'Authorization': 'Bearer ' + app_token_global}).json()

        users = relationship.get("value")
        _relatedusers = list()
        for user in users:
            _relatedusers.append({"id": user.get("id"), "mail": user.get("mail")})

        db.groups.insert_one({"id": _groupId, "displayName": _displayName, "description": _groupDescription, "mail": _groupMail, "members": _relatedusers})

    return jsonify("Groups have been imported")

@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))

@app.route("/graphcall")
def graphcall():
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    graph_data = requests.get(  # Use token to call downstream service
        app_config.ENDPOINT,
        headers={'Authorization': 'Bearer ' + token['access_token']},
        ).json()
    return render_template('display.html', result=graph_data)


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache

def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)

def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result

app.jinja_env.globals.update(_build_auth_code_flow=_build_auth_code_flow)  # Used in template

if __name__ == "__main__":
    app.run()

