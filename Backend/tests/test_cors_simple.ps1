#!/usr/bin/env pwsh
# Simple CORS test without crashing backend

Write-Host "`n🔊 SIMPLE CORS TEST`n" -ForegroundColor Cyan

# Get first song
$songsUrl = "http://127.0.0.1:5000/songs"
Write-Host "Fetching songs from $songsUrl..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri $songsUrl -Method GET
    
    # Find first valid song (not .gitkeep)
    $validSongs = $response.songs | Where-Object { 
        $_.file_id -and 
        $_.file_id -ne '' -and 
        $_.file_id -notlike '*.gitkeep'
    }
    
    if ($validSongs.Count -eq 0) {
        Write-Host "❌ No valid songs found. Upload a song first." -ForegroundColor Red
        exit 1
    }
    
    $testSong = $validSongs[0]
    
    Write-Host "✅ Found test song:" -ForegroundColor Green
    Write-Host "   Title: $($testSong.title)" -ForegroundColor Gray
    Write-Host "   Artist: $($testSong.artist)" -ForegroundColor Gray
    Write-Host "   File ID: $($testSong.file_id)" -ForegroundColor Gray
    Write-Host "   URL: $($testSong.url)`n" -ForegroundColor Gray
    
    # Test download with headers
    Write-Host "Testing CORS headers on download endpoint..." -ForegroundColor Yellow
    
    $downloadResponse = Invoke-WebRequest -Uri $testSong.url -Method GET
    
    $allowOrigin = $downloadResponse.Headers['Access-Control-Allow-Origin']
    $allowMethods = $downloadResponse.Headers['Access-Control-Allow-Methods']
    $contentType = $downloadResponse.Headers['Content-Type']
    
    Write-Host "`nResponse Headers:" -ForegroundColor Cyan
    Write-Host "  Status: $($downloadResponse.StatusCode)" -ForegroundColor Gray
    Write-Host "  Content-Type: $contentType" -ForegroundColor Gray
    Write-Host "  Access-Control-Allow-Origin: $allowOrigin" -ForegroundColor Gray
    Write-Host "  Access-Control-Allow-Methods: $allowMethods`n" -ForegroundColor Gray
    
    # Check result
    if ($allowOrigin -eq '*') {
        Write-Host "🎉 SUCCESS: CORS Headers Configured Correctly!" -ForegroundColor Green
        Write-Host "`nWeb Audio API will work:" -ForegroundColor White
        Write-Host "  ✅ createMediaElementSource() will have audio" -ForegroundColor Green
        Write-Host "  ✅ AudioContext can analyze audio" -ForegroundColor Green
        Write-Host "  ✅ No 'node will output silence' warnings`n" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ FAIL: CORS headers missing or incorrect" -ForegroundColor Red
        Write-Host "  Expected: Access-Control-Allow-Origin: *" -ForegroundColor Yellow
        Write-Host "  Got: $allowOrigin`n" -ForegroundColor Yellow
        exit 1
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
