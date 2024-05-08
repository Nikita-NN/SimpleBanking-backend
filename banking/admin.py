from django.contrib import admin

from banking.models import *

admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(User)
