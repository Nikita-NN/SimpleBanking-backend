from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.middleware.csrf import get_token
from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Account, Transaction
from .serializers import UserSerializer, AccountSerializer, TransactionSerializer


class RegisterAPIView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        date_of_birth = request.data.get('date_of_birth')

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            password=make_password(password)
        )
        user.save()

        return Response({"success": "User created successfully"}, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    def get(self, request):
        csrf_token = get_token(request)
        return JsonResponse({'csrf_token': csrf_token})

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request=request._request, username=username, password=password)
        if user is not None:
            auth_login(request._request, user)
            return Response({"success": "Login successful"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)


class ProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response({"success": "Logout"}, status=status.HTTP_200_OK)


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Account.objects.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_accounts = Account.objects.filter(user=self.request.user)
        user_transactions = Transaction.objects.filter(
            Q(from_account__in=user_accounts) | Q(to_account__in=user_accounts)
        )
        serializer = TransactionSerializer(user_transactions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def last_transactions(self, request):
        user = self.request.user
        user_transactions = Transaction.objects.filter(
            Q(from_account__user=user) | Q(to_account__user=user)
        ).order_by('-date')[:5]

        serializer = TransactionSerializer(user_transactions, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            transaction_data = serializer.validated_data
            amount = transaction_data.get('amount')
            from_account_number = transaction_data.get('from_account')
            to_account_number = transaction_data.get('to_account')

            from_account = Account.objects.get(account_number=from_account_number.account_number)
            to_account = Account.objects.get(account_number=to_account_number.account_number)

            if from_account.user != self.request.user:
                return Response({'error': 'You do not have permission to perform this action'},
                                status=status.HTTP_403_FORBIDDEN)

            if from_account.balance < amount:
                return Response({"error": "Insufficient funds."}, status=status.HTTP_400_BAD_REQUEST)

            internal = from_account.user == to_account.user

            with transaction.atomic():

                from_account.balance -= amount
                from_account.save()
                withdrawal_transaction = Transaction.objects.create(
                    amount=amount,
                    transaction_type='withdrawal',
                    description=transaction_data.get('description'),
                    internal=internal,
                    from_account=from_account
                )


                to_account.balance += amount
                to_account.save()
                deposit_transaction = Transaction.objects.create(
                    amount=amount,
                    transaction_type='deposit',
                    description=transaction_data.get('description'),
                    internal=internal,
                    to_account=to_account
                )

            return Response({
                "withdrawal_transaction": TransactionSerializer(withdrawal_transaction).data,
                "deposit_transaction": TransactionSerializer(deposit_transaction).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
