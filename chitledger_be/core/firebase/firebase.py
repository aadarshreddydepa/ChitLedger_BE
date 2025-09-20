import firebase_admin
from firebase_admin import credentials

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        try:
            print("🔥 Initializing Firebase...")
            cred = credentials.Certificate("/Users/kancharakuntlavineethreddy/Developer/Project/ChitLedger/ChitLedger_BE/chitledger_be/core/firebase/chitledger-firebase-adminsdk-fbsvc-eba8acfd1f.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully!")
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            raise
    else:
        print("Firebase already initialized")

# Initialize Firebase when this module is imported
initialize_firebase()