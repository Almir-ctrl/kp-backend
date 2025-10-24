# ✅ CORS FIX APPLIED - MANUAL TESTING GUIDE

## 🎯 ŠTA JE URAĐENO

CORS headers su dodani na `/download/<file_id>` endpoint za Web Audio API kompatibilnost.

### Izmjene u `app.py` (lines 1014-1095):

```python
@app.route('/download/<file_id>', methods=['GET', 'OPTIONS'])  # ← Dodan OPTIONS
def download_original_file(file_id):
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    # All send_file() calls now include CORS headers:
    response = send_file(file_path, as_attachment=False)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
```

### Additional Fix: `.gitkeep` Filter (lines 358-371):

```python
# Skip .gitkeep and other non-audio files
if entry.startswith('.') or entry in ['.gitkeep', '.gitignore', 'README.md']:
    continue

# Skip if file_id is empty
if not file_id or file_id.strip() == '':
    continue
```

---

## 🚀 KAKO TESTIRATI (MANUELNO)

### KORAK 1: Restart Backend

**Zatvori trenutni backend (Ctrl+C)** pa pokreni:

```powershell
cd C:\Users\almir\AiMusicSeparator-Backend
python app.py
```

**Očekivani output:**
```
 * Running on http://127.0.0.1:5000
INFO:werkzeug:Press CTRL+C to quit
```

---

### KORAK 2: Provjeri Pjesme (Novi Terminal)

```powershell
curl http://127.0.0.1:5000/songs | ConvertFrom-Json | Select-Object -ExpandProperty songs | Select-Object file_id, title, artist | Format-Table
```

**Očekivani output:**
```
file_id                              title                   artist
-------                              -----                   ------
31424681-d079-4f87-9871-52f1bb4b9d33 Sve se osim tuge deli   Unknown Artist
```

**❌ NE SME biti `.gitkeep` u listi!**

---

### KORAK 3: Testiraj CORS Headers

Kopiraj `file_id` iz prethodnog koraka i testiraj:

```powershell
# Zamijeni YOUR_FILE_ID sa stvarnim ID-jem
curl -I http://127.0.0.1:5000/download/YOUR_FILE_ID
```

**Primjer:**
```powershell
curl -I http://127.0.0.1:5000/download/31424681-d079-4f87-9871-52f1bb4b9d33
```

**Očekivani output:**
```
HTTP/1.1 200 OK
Content-Type: audio/wav
Access-Control-Allow-Origin: *                  ← MORA biti *
Access-Control-Allow-Methods: GET, OPTIONS       ← MORA biti prisutno
Access-Control-Allow-Headers: Content-Type       ← MORA biti prisutno
```

---

### KORAK 4: Lion's Roar Studio Test

1. **Hard refresh frontend:**
   - Ctrl + Shift + R u browseru

2. **Otvori DevTools:**
   - F12 → Console tab

3. **Klikni na pjesmu u Library**

4. **Provjeri Console:**
   - ❌ **NE SME biti:** `"cross-origin resource, the node will output silence"`
   - ❌ **NE SME biti:** `"Content-Type of text/html is not supported"`
   - ✅ **Trebalo bi:** Console čist, audio se čuje

5. **Provjeri Network tab:**
   - F12 → Network → Media filter
   - Klikni na request
   - Response Headers trebaju imati:
     ```
     Access-Control-Allow-Origin: *
     Content-Type: audio/mpeg ili audio/wav
     ```

---

## 🎵 OČEKIVANI REZULTATI

| Test | Prije | Poslije |
|------|-------|---------|
| Audio playback | ✅ Radi | ✅ Radi |
| Web Audio API | ❌ Silenced | ✅ **RADI** |
| CORS warnings | ❌ Prisutni | ✅ **NEMA** |
| Content-Type | ❌ text/html | ✅ audio/* |
| .gitkeep u /songs | ❌ Prisutan | ✅ **FILTRIRAN** |

---

## 🐛 TROUBLESHOOTING

### Problem: Backend ne startuje
```powershell
# Ubij sve Python procese
Stop-Process -Name "python" -Force
Start-Sleep -Seconds 2

# Restart
python app.py
```

### Problem: Port 5000 zauzet
```powershell
# Provjeri šta koristi port 5000
netstat -ano | Select-String "5000" | Select-String "LISTENING"

# Ubij proces (zamijeni PID sa stvarnim brojem)
Stop-Process -Id PID -Force
```

### Problem: Lion's Roar Studio još uvijek pokazuje CORS warning
1. **Restartuj backend** (OBAVEZNO!)
2. **Hard refresh browser** (Ctrl+Shift+R)
3. **Restart frontend:**
   ```powershell
   cd C:\Users\almir\lion's-roar-karaoke-studio
   npm run dev
   ```

### Problem: Još uvijek vidim `.gitkeep` u /songs
- Backend **nije restartovan** sa novim kodom
- Zatvori backend (Ctrl+C) i pokreni ponovo

---

## 📝 SUMMARY OF ALL 7 FIXES

| # | Greška | Fix | Status |
|---|--------|-----|--------|
| 1 | Theme picker overflow | Compact layout, 320px width | ✅ FIXED |
| 2 | Missing metadata | Parse from filename/metadata.json | ✅ FIXED |
| 3 | Undefined URLs | Filter .gitkeep, validate file_id | ✅ FIXED |
| 4 | React key warnings | Stable keys using lyric content | ✅ FIXED |
| 5 | Karaoke not selectable | Full Song objects in /karaoke/songs | ✅ FIXED |
| 6 | Audio as HTML (text/html) | Absolute URLs from backend | ✅ FIXED |
| 7 | **Web Audio API CORS** | **Explicit CORS headers on send_file()** | ✅ **FIXED** |

---

## 🎉 FINALNA PROVJERA

Ako sve radi:
- ✅ Audio se čuje u browseru
- ✅ Nema CORS warnings u Console
- ✅ Web Audio API može pristupiti audio podacima
- ✅ Visualizacije i efekti rade
- ✅ .gitkeep nije u /songs listi

**Sve je spremno za produkciju!** 🚀
