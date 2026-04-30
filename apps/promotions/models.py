from accounts.models import StudentPromotion, BatchPromotion


class StudentPromotionProxy(StudentPromotion):
    """Proxy model so Student Promotions appear under the Promotions admin section."""
    class Meta:
        proxy = True
        verbose_name = 'Student Promotion'
        verbose_name_plural = 'Student Promotions'


class BatchPromotionProxy(BatchPromotion):
    """Proxy model so Batch Promotions appear under the Promotions admin section."""
    class Meta:
        proxy = True
        verbose_name = 'Batch Promotion'
        verbose_name_plural = 'Batch Promotions'
