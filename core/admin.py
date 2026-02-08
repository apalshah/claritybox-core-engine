from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Region, Country, Market, Symbol, DataPollingStatus


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email', 'first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'first_name', 'last_name', 'is_active', 'is_staff'),
        }),
    )


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'region')


@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'label')


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'label', 'market', 'country')
    list_filter = ('market',)


@admin.register(DataPollingStatus)
class DataPollingStatusAdmin(admin.ModelAdmin):
    list_display = ('symbol_name', 'market_name', 'status', 'last_updated_at')
    list_filter = ('status', 'market_name')
