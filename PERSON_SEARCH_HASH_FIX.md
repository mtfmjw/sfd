# Person Search Hash Fix

## Problem
Person search was not returning results when searching for names like "大西" even though the person existed in the database.

## Root Cause
The hash fields (`family_name_hash`, `name_hash`, etc.) in the Person model were `None` for all existing records. The search functionality uses these hash fields to search encrypted data, so when the hashes are missing, no search results are returned.

### Why the hashes were missing:
1. Existing records were created before the hash generation was implemented in the `save()` method
2. Records may have been loaded via bulk operations (like `bulk_create` or database imports) that bypass the `save()` method

## Solution
A script was created to regenerate all hash fields for existing Person records:

```python
# regenerate_person_hashes.py
# This script regenerates hash fields for all Person records
```

The script:
1. Iterates through all Person records
2. Generates hashes for all searchable fields (family_name, name, kana, romaji, email, phone, mobile)
3. Updates the database directly using `QuerySet.update()` to avoid triggering save signals

## How Person Search Works

The Person model uses encrypted fields for sensitive information. To enable searching on encrypted data:

1. **Hash Generation**: When a Person record is saved, the `save()` method generates SHA-256 hashes of searchable fields
2. **Hash Storage**: These hashes are stored in separate fields (`family_name_hash`, `name_hash`, etc.)
3. **Search**: When searching, the search term is hashed and compared against the stored hash fields

### Search Implementation
The `PersonAdmin.get_search_results()` method in `sfd/views/person.py`:
- Takes the search term
- Generates a hash using `generate_search_hash()`
- Searches for exact matches across all hash fields
- Returns matching records

### Important Notes
- **Exact match only**: Encrypted field search only supports exact matches
- **Case-sensitive**: The search is case-sensitive
- To search by family name, enter the exact family name (e.g., "大西")
- To search by given name, enter the exact given name
- To search by kana, enter the exact kana

## Future Considerations

### Preventing Missing Hashes
1. **Always use `save()`**: When creating Person records, always use `person.save()` to ensure hashes are generated
2. **Bulk Operations**: After bulk operations, run the regenerate script or ensure hashes are populated
3. **Data Imports**: After importing data, verify and regenerate hashes if needed

### Regenerating Hashes
If you ever need to regenerate hashes (e.g., after a data import), run:
```bash
cd d:\silos\sfd
.venv\Scripts\python.exe regenerate_person_hashes.py
```

### Testing Search
To test the search functionality:
```python
# Test search in Django shell
from sfd.models.person import Person
from sfd.common.encrypted import generate_search_hash
from django.db.models import Q

search_term = "大西"
search_hash = generate_search_hash(search_term)
results = Person.objects.filter(Q(family_name_hash=search_hash))
print(f"Found {results.count()} results")
```

## Related Files
- `sfd/models/person.py` - Person model with hash generation in `save()` method
- `sfd/views/person.py` - PersonAdmin with `get_search_results()` override
- `regenerate_person_hashes.py` - Script to regenerate hashes for existing records
- `sfd/common/encrypted.py` - Contains `generate_search_hash()` function

## Testing
After running the regenerate script:
- Total persons: 1000
- Successfully updated: 1000
- Search for "大西" found: 3 results
  - 大西 昇
  - 大西 雅広
  - 大西 勝巳

The search is now working correctly in the admin interface.
