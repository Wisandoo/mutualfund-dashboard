from django.db import models

class FundFactSheet(models.Model):
    product_code = models.CharField(max_length=50, unique=True, verbose_name="Kode Produk")
    ffs_date = models.DateField(verbose_name="Tanggal FFS")
    data = models.JSONField(verbose_name="Data FFS Lengkap")
    aum = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name="Total AUM")
    latest = models.BooleanField(default=True, verbose_name="Data Terbaru")
    created_datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mutualfund_ffs' 
        verbose_name = 'Fund Fact Sheet'
        verbose_name_plural = 'Fund Fact Sheets'

    def __str__(self):
        return f"{self.product_code} - {self.ffs_date}"
