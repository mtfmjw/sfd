# Admin Search Quick Guide

## 🔍 How to Search in Django Admin (Encrypted Fields)

### ⚠️ Important: EXACT MATCH ONLY

The search only works with **exact values**. Partial searches will not work.

### ✅ What You Can Search For

Search for the EXACT value of any of these fields:

| Field Type | Example Search | Will Find |
|------------|---------------|-----------|
| Family Name | `田中` | All persons with family_name = "田中" |
| Name | `太郎` | All persons with name = "太郎" |
| Family Name Kana | `タナカ` | All persons with family_name_kana = "タナカ" |
| Name Kana | `タロウ` | All persons with name_kana = "タロウ" |
| Family Name Romaji | `Tanaka` | All persons with family_name_romaji = "Tanaka" |
| Name Romaji | `Taro` | All persons with name_romaji = "Taro" |
| Email | `user@example.com` | Person with that exact email |

### ❌ What Will NOT Work

| Search Type | Example | Why It Fails |
|-------------|---------|--------------|
| Partial match | `田` | Won't find "田中" - must be exact |
| Case variation | `tanaka` | Won't find "Tanaka" - case sensitive |
| Combined fields | `田中太郎` | Can't search multiple fields at once |
| Partial email | `@example.com` | Must enter complete email |

### 📝 Step-by-Step Search Instructions

1. Go to Django Admin → Persons
2. In the search box at the top, type the EXACT value you're looking for
3. Press Enter or click the search icon
4. Results will show all persons with that exact value in any searchable field

### 🧪 Testing Your Search

To see what exact values are in your database:

```bash
cd d:\silos\sfd
python test_admin_search.py
```

This will show you:
- All persons in the database
- The exact search terms that will work for each person
- How the hash-based search works

### 💡 Tips

1. **Know the exact value**: You need to know the exact spelling/format
2. **Use one field at a time**: Search for family name OR name, not both
3. **Case matters**: "Tanaka" ≠ "tanaka"
4. **Use filters**: Combine search with other Django admin filters (date ranges, status, etc.)

### 🐛 Troubleshooting

**Problem**: Search returns no results even though you know the person exists

**Solutions**:
1. Check if you typed the EXACT value (including spaces, case, etc.)
2. Try searching by a different field (e.g., email instead of name)
3. Run `python test_admin_search.py` to see the exact searchable values
4. Use Django admin filters instead of search
5. Browse through the list manually if the dataset is small

**Problem**: Search is too restrictive

**Explanation**: This is by design for security. Encrypted data can only be searched by exact hash matches. To enable partial searches, you would need to:
- Decrypt all data (slow and insecure)
- Implement a different encryption scheme (complex)
- Use a separate search index (additional infrastructure)

For now, exact match is the security/usability trade-off we've chosen.
