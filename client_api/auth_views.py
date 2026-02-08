from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    email = request.data.get('email', '').strip().lower()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()
    password = request.data.get('password', '')

    if not all([email, first_name, last_name, password]):
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'Email is already in use'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )

    refresh = RefreshToken.for_user(user)
    return Response({
        'message': 'Registration successful',
        'accessToken': str(refresh.access_token),
        'refreshToken': str(refresh),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email', '').strip().lower()
    password = request.data.get('password', '')

    if not all([email, password]):
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.check_password(password):
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.is_active:
        return Response({'error': 'Account is not active'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    return Response({
        'accessToken': str(refresh.access_token),
        'refreshToken': str(refresh),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    refresh = request.data.get('refresh')
    if not refresh:
        return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh)
        return Response({
            'accessToken': str(token.access_token),
            'refreshToken': str(token),
        })
    except Exception:
        return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user

    if request.method == 'GET':
        return Response({
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    # PUT
    user.first_name = request.data.get('first_name', user.first_name)
    user.last_name = request.data.get('last_name', user.last_name)
    user.save()

    return Response({
        'message': 'Profile updated successfully',
        'first_name': user.first_name,
        'last_name': user.last_name,
    })
