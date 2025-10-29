# Enhanced PowerShell script for git commits with multi-line message support
# Usage: .\git-commit-multiline.ps1 -Title "Main message" -Body @("Line 1", "Line 2", "Line 3")
# Or: .\git-commit-multiline.ps1 -Message "Single line message"

param(
    [Parameter(Mandatory=$false)]
    [string]$Message,
    
    [Parameter(Mandatory=$false)]
    [string]$Title,
    
    [Parameter(Mandatory=$false)]
    [string[]]$Body
)

# Validate parameters
if (-not $Message -and -not $Title) {
    Write-Host "Error: Please provide either -Message or -Title parameter" -ForegroundColor Red
    Write-Host "Usage examples:" -ForegroundColor Yellow
    Write-Host '  .\git-commit-multiline.ps1 -Message "Simple commit message"' -ForegroundColor Gray
    Write-Host '  .\git-commit-multiline.ps1 -Title "Add feature" -Body @("- Implement functionality", "- Add tests", "- Update docs")' -ForegroundColor Gray
    exit 1
}

Write-Host "Adding all changes to git..." -ForegroundColor Green
git add -A

# Build commit message
if ($Message) {
    $commitMessage = $Message
} else {
    $commitMessage = $Title
    if ($Body) {
        foreach ($line in $Body) {
            $commitMessage += "`n`n$line"
        }
    }
}

Write-Host "Committing changes..." -ForegroundColor Green
Write-Host "Message:" -ForegroundColor Cyan
Write-Host $commitMessage -ForegroundColor Gray
Write-Host ""

# Create temporary file for commit message
$tempFile = [System.IO.Path]::GetTempFileName()
$commitMessage | Out-File -FilePath $tempFile -Encoding UTF8

try {
    git commit -F $tempFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully committed changes!" -ForegroundColor Green
    } else {
        Write-Host "Failed to commit changes. Check if there are any changes to commit." -ForegroundColor Yellow
    }
} finally {
    # Clean up temp file
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

Read-Host "Press Enter to continue..."
