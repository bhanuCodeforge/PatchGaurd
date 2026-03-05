from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from datetime import timedelta
import re

User = get_user_model()

class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims
        token['role'] = user.role
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        username = attrs.get(self.username_field)
        users = User.objects.filter(**{self.username_field: username})

        if users.exists():
            user = users.first()
            if user.locked_until and user.locked_until > timezone.now():
                raise AuthenticationFailed("Account locked. Try again later.")

        try:
            data = super().validate(attrs)
        except Exception:
            if users.exists():
                user = users.first()
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.locked_until = timezone.now() + timedelta(minutes=30)
                user.save()
            raise AuthenticationFailed("Invalid credentials or account locked")

        # Success – reset failed attempts and update last_login
        self.user = User.objects.get(**{self.username_field: username})
        self.user.failed_login_attempts = 0
        self.user.locked_until = None
        self.user.last_login = timezone.now()
        self.user.save()
        return data

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_active', 'last_login', 'is_ldap_user', 'date_joined']
        read_only_fields = ['id', 'last_login', 'date_joined']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=12)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'department']

    def create(self, validated_data):
        validated_data['role'] = 'viewer'  # Always register as viewer; admins elevate via admin panel
        return User.objects.create_user(**validated_data)

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=12)

    def validate_new_password(self, value):
        if not re.search(r'[A-Z]', value):
            raise ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', value):
            raise ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'\d', value):
            raise ValidationError("Password must contain at least one digit.")
        if not re.search(r'[^A-Za-z0-9]', value):
            raise ValidationError("Password must contain at least one special character.")
        return value

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Old password is not correct")
        return value
