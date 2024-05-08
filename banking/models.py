from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

from SimpleBanking import settings


class User(AbstractUser):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()

    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )


class Account(models.Model):
    SAVINGS = 'savings'
    CHECKING = 'checking'
    LOAN = 'loan'
    CREDIT_CARD = 'credit_card'
    ACCOUNT_TYPES = [
        (SAVINGS, 'Savings'),
        (CHECKING, 'Checking'),
        (LOAN, 'Loan'),
        (CREDIT_CARD, 'Credit Card'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=15, choices=ACCOUNT_TYPES, default=SAVINGS)
    account_number = models.IntegerField(max_length=20, unique=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='accounts',
        verbose_name='Account holder'
    )

    # Metadata options
    class Meta:
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['user', 'name']

    def __str__(self):
        return f"{self.name} Account #{self.account_number} (Owner: {self.user.username})"


class Transaction(models.Model):
    DEPOSIT = 'deposit'
    WITHDRAWAL = 'withdrawal'
    TRANSFER = 'transfer'
    TRANSACTION_TYPES = [
        (DEPOSIT, 'Deposit'),
        (WITHDRAWAL, 'Withdrawal'),
        (TRANSFER, 'Transfer'),
    ]

    id = models.AutoField(primary_key=True)
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=255, blank=True, null=True)
    internal = models.BooleanField(default=False)

    from_account = models.ForeignKey(
        'Account',
        on_delete=models.CASCADE,
        related_name='transactions_made',
        null=True,
        blank=True,
        verbose_name='From Account'
    )
    to_account = models.ForeignKey(
        'Account',
        on_delete=models.CASCADE,
        related_name='transactions_received',
        null=True,
        blank=True,
        verbose_name='To Account'
    )

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-date']

    def __str__(self):
        internal_label = "Internal" if self.internal else "External"
        return f"{self.transaction_type.capitalize()} of ${self.amount} on {self.date.strftime('%Y-%m-%d')} ({internal_label})"
