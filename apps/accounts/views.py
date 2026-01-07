from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

from .serializers import LoginSerializer, UserSerializer, UserCreateSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint.
    Returns authentication token and user details.
    """
    serializer = LoginSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    user = serializer.validated_data['user']

    # Get or create token
    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user': UserSerializer(user).data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint.
    Deletes the user's authentication token.
    """
    try:
        # Delete the user's token to logout
        request.user.auth_token.delete()
        return Response({
            'detail': 'Successfully logged out.'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'detail': 'Something went wrong.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_view(request):
    """
    Get current user's profile information.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_user(request):
    """
    Create a new user account.

    Accepts:
    - username (required, unique)
    - email (required, unique)
    - password (required, min 8 chars)
    - password_confirm (required, must match password)
    - first_name (optional)
    - last_name (optional)

    Returns:
    - Authentication token
    - User details
    """
    serializer = UserCreateSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Automatically create authentication token for the new user
        token = Token.objects.create(user=user)

        return Response({
            'message': 'User created successfully.',
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
