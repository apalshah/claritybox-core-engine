from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'customuser'

    def __str__(self):
        return self.email


class Region(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        db_table = 'regions'

    def __str__(self):
        return self.name


class Country(models.Model):
    code = models.CharField(max_length=5, unique=True)
    name = models.CharField(max_length=50)
    region = models.ForeignKey(Region, on_delete=models.CASCADE)

    class Meta:
        db_table = 'countries'

    def __str__(self):
        return self.name


class Market(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    label = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'markets'

    def __str__(self):
        return self.label or self.name


class Symbol(models.Model):
    name = models.CharField(max_length=255)
    label = models.CharField(max_length=255, blank=True, null=True)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, blank=True, null=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        db_table = 'symbols'

    def __str__(self):
        return self.name


class BaseMarketData(models.Model):
    """Abstract base for all 5 market data tables."""
    price_timestamp = models.DateTimeField()
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, blank=True, null=True)
    mv_score = models.IntegerField(blank=True, null=True)
    cb_score = models.IntegerField(blank=True, null=True)
    aes_leverage_moderate = models.IntegerField(blank=True, null=True)
    aes_leverage_aggressive = models.IntegerField(blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.symbol} - {self.price_timestamp}"


class StockMarketData(BaseMarketData):
    """Abstract base for stock/index tables with Decimal OHLCV."""
    open = models.DecimalField(max_digits=12, decimal_places=2)
    high = models.DecimalField(max_digits=12, decimal_places=2)
    low = models.DecimalField(max_digits=12, decimal_places=2)
    close = models.DecimalField(max_digits=12, decimal_places=2)
    volume_number = models.BigIntegerField(blank=True, null=True)

    class Meta(BaseMarketData.Meta):
        abstract = True


class IndiaStocksIndexes(StockMarketData):
    class Meta:
        db_table = 'india_stocks_indexes'
        indexes = [
            models.Index(fields=['price_timestamp']),
            models.Index(fields=['symbol']),
        ]


class UsStocksIndexes(StockMarketData):
    class Meta:
        db_table = 'us_stocks_indexes'
        indexes = [
            models.Index(fields=['price_timestamp']),
            models.Index(fields=['symbol']),
        ]


class InternationalStocksIndexes(StockMarketData):
    region = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'international_stocks_indexes'
        indexes = [
            models.Index(fields=['price_timestamp']),
            models.Index(fields=['symbol']),
        ]


class Crypto(BaseMarketData):
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume_number = models.FloatField()
    volume_usd = models.FloatField()
    bitmex_funding_rate = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)

    class Meta:
        db_table = 'crypto'
        indexes = [
            models.Index(fields=['price_timestamp']),
            models.Index(fields=['symbol']),
        ]


class PreciousMetals(StockMarketData):
    class Meta:
        db_table = 'precious_metals'
        indexes = [
            models.Index(fields=['price_timestamp']),
            models.Index(fields=['symbol']),
        ]


class DataPollingStatus(models.Model):
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    symbol_name = models.CharField(max_length=255)
    market_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='ready')
    last_updated_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'data_polling_status'
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.symbol_name} - {self.status}"


class PollingLog(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, blank=True, null=True)
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    rows_updated = models.IntegerField(blank=True, null=True)
    time_to_execute = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'polling_logs'
        indexes = [
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.symbol} - {self.status} - {self.created_at}"
