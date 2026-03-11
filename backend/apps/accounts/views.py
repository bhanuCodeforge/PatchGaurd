from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.decorators import action
from .serializers import (
    CustomTokenObtainSerializer, UserSerializer, UserCreateSerializer, PasswordChangeSerializer,
    AuditLogSerializer
)
from .permissions import IsAdmin, IsOperatorOrAbove
from .models import AuditLog
from common.pagination import StandardPageNumberPagination

User = get_user_model()

@extend_schema(tags=["Auth"])
class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainSerializer

@extend_schema(tags=["Auth"])
class RegisterView(generics.CreateAPIView):
    """
    Public registration endpoint. Creates a new user with role='viewer' by default.
    Returns JWT tokens on success so the user is immediately logged in.
    """
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['username'] = user.username
        refresh['email'] = user.email
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)

@extend_schema(tags=["Auth"])
class RefreshView(TokenRefreshView):
    pass

@extend_schema(tags=["Auth"])
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=["Auth"])
class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.last_password_change = timezone.now()
            user.must_change_password = False
            user.save()
            return Response({"detail": "Password successfully changed"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=["Auth"])
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            # Restrict fields that can be updated via profile
            allowed_fields = ['first_name', 'last_name', 'department']
            update_data = {k: v for k, v in serializer.validated_data.items() if k in allowed_fields}
            
            for attr, value in update_data.items():
                setattr(request.user, attr, value)
            request.user.save()
            
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(tags=["Users"])
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsAdmin]
    filterset_fields = ["role", "is_active", "is_ldap_user"]
    search_fields = ["username", "email", "first_name", "last_name", "department"]
    ordering_fields = ["username", "date_joined", "last_login"]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
        
    def perform_create(self, serializer):
        user = serializer.save()
        AuditLog.objects.create(
            user=self.request.user,
            action=f"Created user {user.username}",
            resource_type="user",
            resource_id=user.id
        )

    def perform_update(self, serializer):
        user = serializer.save()
        AuditLog.objects.create(
            user=self.request.user,
            action=f"Updated user {user.username}",
            resource_type="user",
            resource_id=user.id
        )
        
    def perform_destroy(self, instance):
        AuditLog.objects.create(
            user=self.request.user,
            action=f"Deleted user {instance.username}",
            resource_type="user",
            resource_id=instance.id
        )
        instance.delete()

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        user = self.get_object()
        user.locked_until = timezone.now() + timezone.timedelta(days=36500) # Lock indefinitely
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"Locked user {user.username}",
            resource_type="user",
            resource_id=user.id
        )
        return Response({"status": "User locked"})

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        user = self.get_object()
        user.locked_until = None
        user.failed_login_attempts = 0
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"Unlocked user {user.username}",
            resource_type="user",
            resource_id=user.id
        )
        return Response({"status": "User unlocked"})

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = ''.join(secrets.choice(alphabet) for i in range(16))
        # Ensure it has lowercase, uppercase, digit, special char (hacky way, just append them)
        temp_password += 'aA1!'
        user.set_password(temp_password)
        user.must_change_password = True
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"Reset password for user {user.username}",
            resource_type="user",
            resource_id=user.id
        )
        return Response({"status": "Password reset", "temporary_password": temp_password})

    @action(detail=True, methods=["post"])
    def change_role(self, request, pk=None):
        user = self.get_object()
        new_role = request.data.get("role")
        if new_role not in [r[0] for r in User.Role.choices]:
            return Response({"error": "Invalid role"}, status=status.HTTP_400_BAD_REQUEST)
        user.role = new_role
        user.save()
        AuditLog.objects.create(
            user=request.user,
            action=f"Changed role for user {user.username} to {new_role}",
            resource_type="user",
            resource_id=user.id
        )
        return Response({"status": f"Role changed to {new_role}"})

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly interface for global audit logs. Restricted to Operators/Admins.
    """
    queryset = AuditLog.objects.all().select_related('user').order_by('-timestamp')
    serializer_class = AuditLogSerializer
    permission_classes = [IsOperatorOrAbove]
    pagination_class = StandardPageNumberPagination
    filterset_fields = ['resource_type', 'user']
    search_fields = ['action', 'user__username']
