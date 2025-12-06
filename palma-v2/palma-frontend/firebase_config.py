import pyrebase

firebase_config = {
    "apiKey": "AIzaSyCfRZeUKmefUQ2-dI63HjaETbPoDfdz7Go",
    "authDomain": "palmacountv2.firebaseapp.com",
    "databaseURL": "",
    "projectId": "palmacountv2",
    "storageBucket": "palmacountv2.firebasestorage.app",
    "messagingSenderId": "21033772652",
    "appId": "1:21033772652:web:0eeb6394fb007f86731a49",
    "measurementId": "G-DLRPDTQVW4"
}

firebase = pyrebase.initialize_app(firebase_config)

auth = firebase.auth()
