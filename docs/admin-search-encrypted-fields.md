# Django Admin Search with Encrypted Fields

## Overview

The Person model uses encrypted fields for sensitive data (names, email, phone numbers). To enable searching while maintaining encryption, we use **hash-based search** with SHA-256 hashes.

## Important Limitation: Exact Match Only

⚠️ **CRITICAL**: Encrypted field search only supports **EXACT MATCHES**. This is a fundamental limitation of hash-based search.

### Why Only Exact Matches?

Hash functions are one-way and deterministic:
- `hash("田中")` → `abc123...`
- `hash("田中太郎")` → `xyz789...` (completely different!)

Since the hashes are completely different, searching for "田中" will NOT find "田中太郎".

## How to Search in Django Admin

### Searchable Fields

You can search by any of these fields (exact match required):
- **Family Name** (姓)
- **Name** (名)
- **Family Name Kana** (姓カナ)
- **Name Kana** (名カナ)
- **Family Name Romaji** (姓ローマ字)
- **Name Romaji** (名ローマ字)
- **Email** (メールアドレス)

### Search Examples

✅ **Will Work**:
- Search `田中` → Finds all persons with family_name = "田中"
- Search `太郎` → Finds all persons with name = "太郎"
- Search `タナカ` → Finds all persons with family_name_kana = "タナカ"
- Search `user@example.com` → Finds person with that exact email

❌ **Will NOT Work**:
- Search `田` → Will not find "田中" (partial match)
- Search `tanaka` → Will not find "Tanaka" (case-sensitive)
- Search `田中太郎` → Will not find records where family_name="田中" and name="太郎" (must search one field at a time)

## Technical Implementation

### Database Schema

Hash fields added to the Person model:
```sql
family_name_hash         VARCHAR(64) INDEXED
name_hash                VARCHAR(64) INDEXED
family_name_kana_hash    VARCHAR(64) INDEXED
name_kana_hash           VARCHAR(64) INDEXED
family_name_romaji_hash  VARCHAR(64) INDEXED
name_romaji_hash         VARCHAR(64) INDEXED
email_hash               VARCHAR(64) INDEXED
phone_number_hash        VARCHAR(64) INDEXED
mobile_number_hash       VARCHAR(64) INDEXED
```

### Admin Search Override

The `PersonAdmin.get_search_results()` method is overridden to:
1. Generate SHA-256 hash of the search term
2. Query all hash fields for exact matches
3. Return matching records

```python
def get_search_results(self, request, queryset, search_term):
    if not search_term:
        return queryset, False
    
    search_hash = generate_search_hash(search_term)
    search_query = Q(family_name_hash=search_hash) | \
                   Q(name_hash=search_hash) | \
                   Q(family_name_kana_hash=search_hash) | \
                   Q(name_kana_hash=search_hash) | \
                   Q(family_name_romaji_hash=search_hash) | \
                   Q(name_romaji_hash=search_hash) | \
                   Q(email_hash=search_hash)
    
    filtered_queryset = queryset.filter(search_query)
    return filtered_queryset, filtered_queryset.exists()
```

### Hash Generation

Hashes are automatically generated when saving records:
```python
def save(self, *args, **kwargs):
    # Generate hashes for encrypted fields
    if self.family_name:
        self.family_name_hash = generate_search_hash(self.family_name)
    if self.name:
        self.name_hash = generate_search_hash(self.name)
    # ... etc for all encrypted fields
    super().save(*args, **kwargs)
```

## Testing the Search

Run the test script to see what search terms will work:
```bash
python test_admin_search.py
```

This will show you:
- All persons in the database
- The exact search terms that will find each person
- Hash values stored in the database

## Alternative Search Methods

If you need partial or fuzzy search, consider:

### 1. Programmatic Search (In Code)
```python
# Search by exact family name
Person.objects.search_exact(family_name="田中")

# Search by exact email
Person.objects.search_by_email("user@example.com")
```

### 2. Multiple Queries
```python
# Find all persons with family_name "田中"
persons = Person.objects.search_exact(family_name="田中")

# Then filter in Python for other criteria
results = [p for p in persons if "太郎" in p.name]
```

### 3. Decrypt and Filter
For administrative tasks where decryption is acceptable:
```python
# Get all persons
all_persons = Person.objects.all()

# Decrypt and filter in Python
results = [p for p in all_persons if "田中" in p.family_name]
```

⚠️ **Warning**: Decrypting many records can be slow and memory-intensive.

## Future Improvements

Potential enhancements to consider:

1. **Phonetic Search**: Add soundex/metaphone hashes for fuzzy matching
2. **N-gram Hashing**: Store hashes of substrings for partial matching
3. **Searchable Encryption**: Use schemes like Order-Preserving Encryption (OPE)
4. **Separate Search Index**: Maintain a separate encrypted search index

Each approach has security and performance trade-offs.

## Security Notes

- Hash fields use SHA-256 (256-bit security)
- Hashes are indexed for fast lookup
- Original encrypted data remains secure
- Hash collisions are extremely unlikely (2^256 possible hashes)
- Dictionary attacks are possible if search space is small (e.g., common names)

## Support

If you need to search by partial matches or other patterns, please discuss alternative implementations with the development team.
