from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Review, ReviewSummary


@receiver(post_save, sender=Review)
def update_review_summary_on_save(sender, instance, **kwargs):
    """Update review summary when a review is saved"""
    if instance.status == 'approved':
        ReviewSummary.update_for_product(instance.product)


@receiver(post_delete, sender=Review)
def update_review_summary_on_delete(sender, instance, **kwargs):
    """Update review summary when a review is deleted"""
    ReviewSummary.update_for_product(instance.product)