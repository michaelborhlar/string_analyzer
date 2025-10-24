from django.db import models

# Create your models here.

import hashlib


def compute_properties(value: str) -> dict:
    """Compute all required string properties."""
    sha = hashlib.sha256(value.encode("utf-8")).hexdigest()
    length = len(value)
    is_palindrome = value.lower() == value[::-1].lower()
    unique_characters = len(set(value))
    word_count = len(value.split())

    # character frequency map
    freq = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1

    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha,
        "character_frequency_map": freq,
    }


class StoredString(models.Model):
    """Model to store analyzed strings and their properties."""
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    value = models.TextField(unique=True)
    properties = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        computed = compute_properties(self.value)
        self.id = computed["sha256_hash"]
        self.properties = computed
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.value[:30]}..."
