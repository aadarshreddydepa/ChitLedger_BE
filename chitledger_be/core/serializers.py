from rest_framework import serializers
from .models import User


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ["user_id", "phone_number", "name", "password"]
        read_only_fields = ["user_id"] #check what is ready only later 

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        user.is_verified = True   # mark as verified (after OTP)
        user.save()
        return user


class UserSigninSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
