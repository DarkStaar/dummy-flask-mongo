from crypt import methods
from flask import Flask
from flask import jsonify, request

import pymongo
from pymongo import MongoClient

from bson.json_util import dumps

from bson.objectid import ObjectId

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

if __name__ == "__main__":
   app.run(host = '0.0.0.0', debug = True, port = '9999')

try:
    mongo = MongoClient('host.docker.internal', 27017)
    
    db = mongo.testflask
    
    mongo.server_info() #Triggers exception if it cant conenct to DB
    
    db.list_collection_names()
    
    print("Database is connected!")
    
except:
    print("Error while connecting to DB")


@app.route("/user/<username>/", methods = ["GET"])
def findUser(username):
    
    if username:
        resp = db.users.find_one({"username" : username})
        if resp is not None:
            response = list()
            response.append({"username": resp["username"], "email": resp["email"], "password": resp["password"]})
        
        return jsonify(response)
    else:
        not_found()

@app.route("/users", methods = ["GET"])     
def findUsers():  
    holder = list()
    for i in db.users.find():
        holder.append({"username": i["username"], "email": i["email"], "password": i["password"]})
    return jsonify(holder)

@app.route('/users/add', methods = ['POST'])
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
    
@app.errorhandler(404)
def not_found(error = None):
    message = {
        'status_code': 404,
        'message' : 'Not Found' + request.url
    }
    
    resp = jsonify(message)
    
    resp.status_code = 404
    
    return resp