from django.db import models
import hashlib

def compute_properties(value: str) -> dict:
    """Compute all required string properties."""
    # Generate SHA256 hash
    sha256_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    
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
        "sha256_hash": sha256_hash,  # This will be the same as the id
        "character_frequency_map": freq,
    }

class StoredString(models.Model):
    id = models.CharField(max_length=64, primary_key=True, editable=False)
    value = models.TextField(unique=True)
    properties = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        computed = compute_properties(self.value)
        # Use the SHA256 hash as ID
        self.id = computed["sha256_hash"]
        self.properties = computed
        super().save(*args, **kwargs)
