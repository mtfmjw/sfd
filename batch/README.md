# Batch Scripts for Windows Development

This directory contains batch and PowerShell scripts to streamline development tasks on Windows, particularly addressing Windows Command Prompt limitations.

## Git Commit Scripts

### Problem: Multi-line Commit Messages on Windows

Windows Command Prompt interprets lines starting with hyphens (`-`) as separate commands, causing errors with multi-line git commit messages.

### Solutions Available

#### 1. `git-commit.bat` - Simple Single-line Commits

```cmd
batch\git-commit.bat "Your commit message"
```

- Basic commit functionality
- Works with single-line messages only

#### 2. `git-commit-multiline.bat` - Enhanced Multi-line Support

```cmd
batch\git-commit-multiline.bat "Title" "Description line 1" "Description line 2"
```

- Handles multi-line commit messages safely
- Each argument becomes a separate line in the commit message
- Uses temporary files to avoid CMD parsing issues
- Automatically adds `git add -A`

**Example:**

```cmd
batch\git-commit-multiline.bat "Add new feature" "- Implement user authentication" "- Add password validation" "- Update documentation"
```

#### 3. `git-commit-multiline.ps1` - PowerShell Solution

```powershell
# Single line
.\batch\git-commit-multiline.ps1 -Message "Simple commit message"

# Multi-line with array
.\batch\git-commit-multiline.ps1 -Title "Add feature" -Body @("- Implement functionality", "- Add tests", "- Update docs")
```

- Most flexible solution
- Supports both single-line and multi-line formats
- Better error handling and formatting
- Works in PowerShell environments

## Other Development Scripts

### Database Management

- `create_database.bat` - Set up PostgreSQL database
- `migrate.bat` - Run Django migrations
- `makemigrations.bat` - Generate Django migrations
- `clear_migrations.bat` - Clean migration files

### Django Development

- `run_server.bat` - Start Django development server
- `create_superuser.bat` - Create Django admin user
- `inspectdb.bat` - Generate models from existing database

### Environment Management

- `activate.bat` - Activate Python virtual environment
- `env.bat` - Environment variable utilities

## Usage Tips

1. **For developers using CMD**: Use the `.bat` scripts
2. **For developers using PowerShell**: Use the `.ps1` scripts
3. **For multi-line commits**: Always use the multi-line versions to avoid hyphen errors
4. **For automation**: Scripts can be called from VS Code tasks or CI/CD pipelines

## Alternative Methods

If you prefer not to use these scripts:

### Method 1: Temporary Files

```cmd
echo Your commit message > temp_commit.txt
echo. >> temp_commit.txt
echo - First bullet point >> temp_commit.txt
git add -A
git commit -F temp_commit.txt
del temp_commit.txt
```

### Method 2: Git GUI

```cmd
git add -A
git commit
# Opens your default editor for commit message
```

### Method 3: Escape Characters (Limited Success)

```cmd
git commit -m "Title^

- Bullet point 1^

- Bullet point 2"
```

The scripts in this directory provide the most reliable solutions for Windows development environments.
