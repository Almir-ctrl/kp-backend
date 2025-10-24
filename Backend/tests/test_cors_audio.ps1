#!/usr/bin/env pwsh
# Test CORS headers on audio download endpoints

Write-Host "`n🔊 CORS AUDIO HEADERS TEST" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan

$BASE_URL = "http://127.0.0.1:5000"

# First, get a song to test with
Write-Host "`n📡 Fetching songs to get test file_id..." -ForegroundColor Yellow

try {
    $songsResponse = Invoke-RestMethod -Uri "$BASE_URL/songs" -Method GET -ErrorAction Stop
    
    if ($songsResponse.count -eq 0) {
        Write-Host "⚠️  No songs found. Upload a song first:" -ForegroundColor Yellow
        Write-Host "   curl -F 'file=@song.mp3' $BASE_URL/upload" -ForegroundColor White
        exit 0
    }
    
    $testSong = $songsResponse.songs[0]
    $fileId = $testSong.file_id
    $downloadUrl = "$BASE_URL/download/$fileId"
    
    Write-Host "✅ Found test song: $($testSong.title) - $($testSong.artist)" -ForegroundColor Green
    Write-Host "   File ID: $fileId" -ForegroundColor Gray
    Write-Host "   Download URL: $downloadUrl" -ForegroundColor Gray
    
    # Test 1: OPTIONS request (CORS preflight)
    Write-Host "`n📋 Test 1: OPTIONS Request (CORS Preflight)" -ForegroundColor Yellow
    Write-Host "-" * 60 -ForegroundColor Gray
    
    try {
        $optionsResponse = Invoke-WebRequest -Uri $downloadUrl -Method OPTIONS -ErrorAction Stop
        
        $allowOrigin = $optionsResponse.Headers['Access-Control-Allow-Origin']
        $allowMethods = $optionsResponse.Headers['Access-Control-Allow-Methods']
        $allowHeaders = $optionsResponse.Headers['Access-Control-Allow-Headers']
        
        Write-Host "   Status: $($optionsResponse.StatusCode)" -ForegroundColor Gray
        
        if ($allowOrigin) {
            Write-Host "   ✅ Access-Control-Allow-Origin: $allowOrigin" -ForegroundColor Green
        } else {
            Write-Host "   ❌ MISSING: Access-Control-Allow-Origin header" -ForegroundColor Red
        }
        
        if ($allowMethods) {
            Write-Host "   ✅ Access-Control-Allow-Methods: $allowMethods" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  MISSING: Access-Control-Allow-Methods header" -ForegroundColor Yellow
        }
        
        if ($allowHeaders) {
            Write-Host "   ✅ Access-Control-Allow-Headers: $allowHeaders" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  MISSING: Access-Control-Allow-Headers header" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "   ⚠️  OPTIONS method not supported (may still work)" -ForegroundColor Yellow
        Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Gray
    }
    
    # Test 2: GET request with CORS headers
    Write-Host "`n📋 Test 2: GET Request (Actual Audio Download)" -ForegroundColor Yellow
    Write-Host "-" * 60 -ForegroundColor Gray
    
    try {
        $getResponse = Invoke-WebRequest -Uri $downloadUrl -Method GET -ErrorAction Stop
        
        $allowOrigin = $getResponse.Headers['Access-Control-Allow-Origin']
        $contentType = $getResponse.Headers['Content-Type']
        $contentLength = $getResponse.Headers['Content-Length']
        
        Write-Host "   Status: $($getResponse.StatusCode)" -ForegroundColor Gray
        Write-Host "   Content-Type: $contentType" -ForegroundColor Gray
        Write-Host "   Content-Length: $contentLength bytes" -ForegroundColor Gray
        
        if ($allowOrigin) {
            Write-Host "   ✅ Access-Control-Allow-Origin: $allowOrigin" -ForegroundColor Green
            
            if ($allowOrigin -eq '*') {
                Write-Host "      ✅ Wildcard (*) allows all origins" -ForegroundColor Green
            } else {
                Write-Host "      ℹ️  Specific origin: $allowOrigin" -ForegroundColor Cyan
            }
        } else {
            Write-Host "   ❌ MISSING: Access-Control-Allow-Origin header" -ForegroundColor Red
            Write-Host "      This will cause 'cross-origin resource' warning!" -ForegroundColor Red
        }
        
        # Verify it's actually audio
        if ($contentType -notmatch 'audio/') {
            Write-Host "   ⚠️  WARNING: Content-Type is not audio/* ($contentType)" -ForegroundColor Yellow
        } else {
            Write-Host "   ✅ Content-Type is valid audio format" -ForegroundColor Green
        }
        
    } catch {
        Write-Host "   ❌ FAILED: Cannot download audio" -ForegroundColor Red
        Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Test 3: Verify in browser context
    Write-Host "`n📋 Test 3: Web Audio API Compatibility" -ForegroundColor Yellow
    Write-Host "-" * 60 -ForegroundColor Gray
    
    if ($allowOrigin -eq '*') {
        Write-Host "   ✅ PASS: Web Audio API will work" -ForegroundColor Green
        Write-Host "      createMediaElementSource() will have audio" -ForegroundColor Green
        Write-Host "      AudioContext will be able to analyze audio" -ForegroundColor Green
    } elseif ($allowOrigin) {
        Write-Host "   ⚠️  PARTIAL: Web Audio API may work for specific origin" -ForegroundColor Yellow
        Write-Host "      Only works if frontend matches: $allowOrigin" -ForegroundColor Yellow
    } else {
        Write-Host "   ❌ FAIL: Web Audio API will output silence" -ForegroundColor Red
        Write-Host "      Browser will show:" -ForegroundColor Red
        Write-Host "      'cross-origin resource, the node will output silence'" -ForegroundColor Red
    }
    
    # Summary
    Write-Host "`n" + ("=" * 60) -ForegroundColor Cyan
    
    if ($allowOrigin -eq '*') {
        Write-Host "🎉 SUCCESS: CORS Headers Configured Correctly!" -ForegroundColor Green
        Write-Host "`nYou can now:" -ForegroundColor White
        Write-Host "  ✅ Play audio in browser" -ForegroundColor Green
        Write-Host "  ✅ Use Web Audio API (createMediaElementSource)" -ForegroundColor Green
        Write-Host "  ✅ Analyze audio with AudioContext" -ForegroundColor Green
        Write-Host "  ✅ Create audio visualizations" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "❌ CORS HEADERS MISSING OR INCORRECT" -ForegroundColor Red
        Write-Host "`nProblems:" -ForegroundColor Yellow
        Write-Host "  ❌ Audio will play but Web Audio API won't work" -ForegroundColor Red
        Write-Host "  ❌ createMediaElementSource will output silence" -ForegroundColor Red
        Write-Host "  ❌ AudioContext cannot analyze audio" -ForegroundColor Red
        Write-Host "`nFix:" -ForegroundColor Yellow
        Write-Host "  1. Add CORS headers to /download endpoint in app.py" -ForegroundColor White
        Write-Host "  2. Restart backend server" -ForegroundColor White
        Write-Host "  3. Run this test again" -ForegroundColor White
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
