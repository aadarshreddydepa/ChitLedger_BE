from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # Initialize Firebase when Django app is ready
        try:
            from .firebase.firebase import initialize_firebase
            print("✅ Firebase imported and initialized from apps.py")
        except Exception as e:
            print(f"❌ Failed to initialize Firebase in apps.py: {e}")