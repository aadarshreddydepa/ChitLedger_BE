# Import Firebase to ensure it's initialized


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.permissions import  IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSignupSerializer, UserSigninSerializer
# import firebase
from firebase_admin import auth as firebase_auth

# ---------- Signup ----------
# Deprecated -- signup logic
# class SignupView(APIView):
#     def post(self, request):
#         serializer = UserSignupSerializer(data=request.data)
#         if serializer.is_valid():
#             user = serializer.save()
#             return Response(
#                 {"message": "User registered successfully", "user_id": user.user_id},
#                 status=status.HTTP_201_CREATED,
#             )
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Signin ----------
class SigninView(APIView):
    def post(self, request):
        serializer = UserSigninSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            password = serializer.validated_data["password"]

            user = authenticate(request, phone_number=phone_number, password=password)
            if not user:
                return Response(
                    {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
                )

            # Generate JWT token
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_id": user.user_id,
                    "name": user.name,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PermissionRequiredView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            print(user)
            response_data = {"success": True}
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "error": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
        
class FirebaseSignupView(APIView):
    def post(self, request):
        try:
            print("🔥 Firebase signup endpoint called")
            
            id_token = request.data.get("idToken")
            fe_phone_number = request.data.get("phoneNumber")
            name = request.data.get("name")
            password = request.data.get("password")

            print(f"Received: phone={fe_phone_number}, name={name}, token_present={bool(id_token)}")

            if not id_token or not password or not name:
                return Response({
                    "error": "idToken, name, and password are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify Firebase token
            print("Verifying Firebase token...")
            decoded_token = firebase_auth.verify_id_token(id_token)
            phone_number = decoded_token.get("phone_number")
            
            print(f"✅ Token verified! Phone from token: {phone_number}")

            if not phone_number:
                return Response({
                    "error": "Phone number not found in token"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Check if user already exists
            if User.objects.filter(phone_number=phone_number).exists():
                return Response({
                    "error": "User with this phone number already exists"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create user
            serializer = UserSignupSerializer(data={
                "phone_number": phone_number,
                "name": name,
                "password": password,
            })

            if serializer.is_valid():
                user = serializer.save()
                print(f"✅ User created successfully: {user.phone_number}")
                return Response({
                    "message": "User registered successfully",
                    "user_id": str(user.user_id),
                    "phone_number": user.phone_number,
                    "name": user.name
                }, status=status.HTTP_201_CREATED)

            print(f"❌ Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except firebase_auth.InvalidIdTokenError as e:
            print(f"❌ Invalid Firebase token: {e}")
            return Response({
                "error": "Invalid Firebase ID token"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"❌ Signup error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Signup failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class FirebasePasswordResetView(APIView):
    def post(self, request):
        try:
            id_token = request.data.get("idToken")
            phone_number = request.data.get("phoneNumber")
            new_password = request.data.get("newPassword")  # Expect "password" key, not "newPassword"

            if not id_token or not phone_number or not new_password:
                return Response({
                    "error": "idToken, phoneNumber, and password are required"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Verify Firebase ID token
            decoded_token = firebase_auth.verify_id_token(id_token)
            token_phone_number = decoded_token.get("phone_number")

            if token_phone_number != phone_number:
                return Response({
                    "error": "Phone number mismatch with token"
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(phone_number=phone_number)
            except User.DoesNotExist:
                return Response({
                    "error": "User not found"
                }, status=status.HTTP_404_NOT_FOUND)

            # Set the new password securely
            user.set_password(new_password)
            user.save()

            return Response({
                "message": "Password reset successful"
            }, status=status.HTTP_200_OK)

        except firebase_auth.InvalidIdTokenError:
            return Response({
                "error": "Invalid Firebase ID token"
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(f"❌ Password reset error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                "error": f"Password reset failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
