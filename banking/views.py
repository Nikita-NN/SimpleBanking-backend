from io import BytesIO

from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.hashers import make_password
from django.db import transaction, connection
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token
from rest_framework import status, generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle , Paragraph
from reportlab.lib.styles import getSampleStyleSheet
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
        user_id = self.request.user.id
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM banking_account WHERE user_id = %s", [user_id])
            rows = cursor.fetchall()
            accounts = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]
        return accounts

    def perform_create(self, serializer):
        user_id = self.request.user.id
        account_data = serializer.validated_data
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO banking_account (name, balance, type, account_number, user_id) VALUES (%s, %s, %s, %s, %s)",
                [account_data['name'], account_data['balance'], account_data['type'], account_data['account_number'], user_id]
            )



class TransactionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        user_id = self.request.user.id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM banking_transaction 
                WHERE from_account_id IN (SELECT id FROM banking_account WHERE user_id = %s)
                OR to_account_id IN (SELECT id FROM banking_account WHERE user_id = %s)
            """, [user_id, user_id])
            rows = cursor.fetchall()
            transactions = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

        transaction_instances = [Transaction(**transaction) for transaction in transactions]
        serializer = TransactionSerializer(transaction_instances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='generate_statement')
    def generate_statement(self, request):
        user_id = self.request.user.id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT t.id, t.date, t.amount, t.transaction_type, t.description,
                       fa.account_number as from_account_number,
                       ta.account_number as to_account_number, t.internal
                FROM banking_transaction t
                LEFT JOIN banking_account fa ON t.from_account_id = fa.id
                LEFT JOIN banking_account ta ON t.to_account_id = ta.id
                WHERE fa.user_id = %s OR ta.user_id = %s
                ORDER BY t.date DESC
            """, [user_id, user_id])
            rows = cursor.fetchall()
            transactions = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

        # Create a PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []

        # Add title
        styles = getSampleStyleSheet()
        title = Paragraph("Transaction Statement", styles['Title'])
        elements.append(title)

        # Prepare table data
        headers = ["ID", "Date", "Amount", "Type", "Description", "From Account", "To Account", "Internal"]
        data = [headers] + [[
            str(transaction['id']),
            str(transaction['date']),
            str(transaction['amount']),
            str(transaction['transaction_type']),
            str(transaction['description']),
            str(transaction['from_account_number']),
            str(transaction['to_account_number']),
            str(transaction['internal'])
        ] for transaction in transactions]

        # Create table
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        # Add table to elements
        elements.append(table)

        # Build PDF
        doc.build(elements)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="transaction_statement.pdf"'
        return response
    
    @action(detail=False, methods=['get'], url_path='transactions_account')
    def transactions_account(self, request):
        account_number = request.query_params.get('account_number')
        if not account_number:
            raise NotFound("Account number must be provided.")

        try:
            account_number = int(account_number)
        except ValueError:
            raise NotFound("Account number must be a valid number.")

        user_id = self.request.user.id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM banking_transaction 
                WHERE (from_account_id = (SELECT id FROM banking_account WHERE account_number = %s AND user_id = %s) 
                OR to_account_id = (SELECT id FROM banking_account WHERE account_number = %s AND user_id = %s))
                ORDER BY date DESC
            """, [account_number, user_id, account_number, user_id])
            rows = cursor.fetchall()
            transactions = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

        transaction_instances = [Transaction(**transaction) for transaction in transactions]
        serializer = TransactionSerializer(transaction_instances, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def last_transactions(self, request):
        user_id = self.request.user.id
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM banking_transaction 
                WHERE from_account_id IN (SELECT id FROM banking_account WHERE user_id = %s)
                OR to_account_id IN (SELECT id FROM banking_account WHERE user_id = %s)
                ORDER BY date DESC LIMIT 5
            """, [user_id, user_id])
            rows = cursor.fetchall()
            transactions = [dict(zip([column[0] for column in cursor.description], row)) for row in rows]

        transaction_instances = [Transaction(**transaction) for transaction in transactions]
        serializer = TransactionSerializer(transaction_instances, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            transaction_data = serializer.validated_data
            amount = transaction_data.get('amount')
            from_account_number = transaction_data.get('from_account').account_number
            to_account_number = transaction_data.get('to_account').account_number

            with connection.cursor() as cursor:
                cursor.execute("SELECT id, balance, user_id FROM banking_account WHERE account_number = %s", [from_account_number])
                from_account = cursor.fetchone()

                cursor.execute("SELECT id, balance, user_id FROM banking_account WHERE account_number = %s", [to_account_number])
                to_account = cursor.fetchone()

                if from_account[2] != self.request.user.id or from_account == to_account:
                    return Response({'error': 'You do not have permission to perform this action'}, status=status.HTTP_403_FORBIDDEN)

                if from_account[1] < amount:
                    return Response({"error": "Insufficient funds."}, status=status.HTTP_400_BAD_REQUEST)

                internal = from_account[2] == to_account[2]

                with transaction.atomic():
                    cursor.execute("UPDATE banking_account SET balance = balance - %s WHERE id = %s", [amount, from_account[0]])
                    cursor.execute("""
                        INSERT INTO banking_transaction 
                        (amount, transaction_type, description, internal, from_account_id, date) 
                        VALUES (%s, 'withdrawal', %s, %s, %s, CURRENT_TIMESTAMP)
                    """, [amount, transaction_data.get('description'), internal, from_account[0]])

                    cursor.execute("UPDATE banking_account SET balance = balance + %s WHERE id = %s", [amount, to_account[0]])
                    cursor.execute("""
                        INSERT INTO banking_transaction 
                        (amount, transaction_type, description, internal, to_account_id, date) 
                        VALUES (%s, 'deposit', %s, %s, %s, CURRENT_TIMESTAMP)
                    """, [amount, transaction_data.get('description'), internal, to_account[0]])

            return Response({"success": "Transaction created successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)