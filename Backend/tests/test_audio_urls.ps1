#!/usr/bin/env pwsh
# Test script to verify audio URLs are absolute and playable

Write-Host "`n🎵 AUDIO URL VERIFICATION TEST" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$BASE_URL = "http://127.0.0.1:5000"

# Test /songs endpoint
Write-Host "`n📡 Testing /songs endpoint..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/songs" -Method GET -ErrorAction Stop
    
    if ($response.count -eq 0) {
        Write-Host "⚠️  No songs found. Upload a song first:" -ForegroundColor Yellow
        Write-Host "   curl -F 'file=@song.mp3' $BASE_URL/upload" -ForegroundColor White
        exit 0
    }
    
    Write-Host "✅ Found $($response.count) songs" -ForegroundColor Green
    
    # Check each song URL
    $allPassed = $true
    
    foreach ($song in $response.songs) {
        Write-Host "`n📝 Song: $($song.title) - $($song.artist)" -ForegroundColor White
        
        # Check URL format
        $url = $song.url
        Write-Host "   URL: $url" -ForegroundColor Gray
        
        # Verify URL is absolute
        if ($url -notmatch '^https?://') {
            Write-Host "   ❌ FAILED: URL is not absolute (doesn't start with http://)" -ForegroundColor Red
            Write-Host "      Got: $url" -ForegroundColor Red
            Write-Host "      Expected: http://127.0.0.1:5000/download/..." -ForegroundColor Red
            $allPassed = $false
            continue
        }
        
        # Verify URL points to backend port 5000
        if ($url -match 'localhost:3000' -or $url -match ':3000/') {
            Write-Host "   ❌ FAILED: URL points to frontend port 3000!" -ForegroundColor Red
            Write-Host "      Got: $url" -ForegroundColor Red
            Write-Host "      Should be: port 5000 (backend)" -ForegroundColor Red
            $allPassed = $false
            continue
        }
        
        # Verify URL contains file_id
        if ($url -notmatch '[a-f0-9-]{36}') {
            Write-Host "   ⚠️  WARNING: URL doesn't contain UUID" -ForegroundColor Yellow
        }
        
        # Test if URL is accessible (HEAD request)
        try {
            $headResponse = Invoke-WebRequest -Uri $url -Method HEAD -ErrorAction Stop
            $contentType = $headResponse.Headers['Content-Type']
            
            Write-Host "   ✅ URL accessible" -ForegroundColor Green
            Write-Host "      Content-Type: $contentType" -ForegroundColor Gray
            
            # Verify Content-Type is audio, not HTML
            if ($contentType -match 'text/html') {
                Write-Host "   ❌ CRITICAL: Content-Type is text/html, not audio!" -ForegroundColor Red
                Write-Host "      This will cause 'Cannot play media' error" -ForegroundColor Red
                $allPassed = $false
            } elseif ($contentType -notmatch 'audio/') {
                Write-Host "   ⚠️  WARNING: Content-Type is not audio/* ($contentType)" -ForegroundColor Yellow
            } else {
                Write-Host "   ✅ Content-Type is valid audio format" -ForegroundColor Green
            }
            
        } catch {
            Write-Host "   ❌ FAILED: URL not accessible" -ForegroundColor Red
            Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Red
            $allPassed = $false
        }
    }
    
    Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
    
    if ($allPassed) {
        Write-Host "🎉 ALL TESTS PASSED!" -ForegroundColor Green
        Write-Host "   All URLs are absolute and point to backend (port 5000)" -ForegroundColor Green
        Write-Host "   All Content-Types are valid audio formats" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ SOME TESTS FAILED" -ForegroundColor Red
        Write-Host "   Fix the errors above and restart backend" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "❌ FAILED: Cannot connect to backend at $BASE_URL" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n   Start backend:" -ForegroundColor Yellow
    Write-Host "   cd C:\Users\almir\AiMusicSeparator-Backend" -ForegroundColor White
    Write-Host "   python app.py" -ForegroundColor White
    exit 1
}
