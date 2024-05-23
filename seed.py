import os
import random

import django
from faker import Faker

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SimpleBanking.settings')
django.setup()

from banking.models import User, Account, Transaction


def generate_random_users_and_accounts(num_users=100, output_file='user_credentials.txt'):
    faker = Faker()

    with open(output_file, 'w') as file:
        for _ in range(num_users):
            username = faker.unique.user_name()
            email = faker.unique.email()
            password = faker.password()
            date_of_birth = faker.date_of_birth(minimum_age=18, maximum_age=90)

            user = User.objects.create_user(
                first_name=faker.first_name(),
                last_name=faker.last_name(),
                username=username,
                email=email,
                date_of_birth=date_of_birth,
                password=password
            )

            # Write username and password to the file
            file.write(f"Username: {username}, Password: {password}\n")

            for _ in range(random.randint(1, 3)):
                account = Account.objects.create(
                    name=faker.word().capitalize() + ' Account',
                    balance=round(random.uniform(1000, 100000), 2),
                    type=random.choice([Account.SAVINGS, Account.CHECKING]),
                    account_number=faker.unique.random_number(digits=10),
                    user=user
                )


                for _ in range(random.randint(5, 10)):
                    transaction_type = random.choice(
                        [Transaction.DEPOSIT, Transaction.WITHDRAWAL, Transaction.TRANSFER])
                    amount = round(random.uniform(100, 10000), 2)
                    description = faker.text(max_nb_chars=25)

                    Transaction.objects.create(
                        amount=amount,
                        transaction_type=transaction_type,
                        description=description,
                        from_account=account if transaction_type != Transaction.DEPOSIT else None,
                        to_account=account if transaction_type != Transaction.WITHDRAWAL else None,
                        internal=random.choice([True, False]),
                    )


if __name__ == '__main__':
    generate_random_users_and_accounts(num_users=10)
