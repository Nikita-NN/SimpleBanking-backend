import random

from rest_framework import serializers

from .models import User, Account, Transaction


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'name', 'type', 'account_number', 'balance']
        read_only_fields = ['account_number', 'balance']

    def create(self, validated_data):
        validated_data['account_number'] = str(random.randint(1000000000, 9999999999))
        validated_data['balance'] = 0
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'date', 'amount', 'transaction_type', 'description', 'internal', 'from_account', 'to_account')

    def to_internal_value(self, data):
        from_account_number = data.get('from_account')
        to_account_number = data.get('to_account')

        try:
            from_account = Account.objects.get(account_number=from_account_number)
            to_account = Account.objects.get(account_number=to_account_number)
        except Account.DoesNotExist:
            raise serializers.ValidationError("One or both accounts do not exist.")

        data['from_account'] = from_account.id
        data['to_account'] = to_account.id

        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['from_account'] = instance.from_account.account_number if instance.from_account else None
        representation['to_account'] = instance.to_account.account_number if instance.to_account else None
        return representation
