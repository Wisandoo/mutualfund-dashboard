from django.contrib import admin
from .models import FundFactSheet

@admin.register(FundFactSheet)
class FundFactSheetAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'ffs_date', 'aum', 'latest', 'created_datetime')
    search_fields = ('product_code',)
    list_filter = ('ffs_date', 'latest')