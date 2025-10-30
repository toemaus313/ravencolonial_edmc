# Release Checklist for v1.3.0

## ✅ Enhancements Implemented

### 1. **Localization Support (l10n)**
- ✅ Added `import l10n` and `import functools`
- ✅ Created `plugin_tl` translation function
- ✅ Wrapped all UI strings with `plugin_tl()`
- ✅ Created `L10n/en.template` with all translatable strings
- ✅ Implemented `prefs_changed()` to refresh UI when language changes

**Benefits:**
- Plugin can be translated to any language EDMC supports
- Automatic UI refresh when user changes language
- Framework ready for community translations

### 2. **Async Error Display**
- ✅ Added `import plug`
- ✅ Implemented `plug.show_error()` in API worker thread
- ✅ Errors now appear in EDMC status bar
- ✅ Localized error messages

**Benefits:**
- Users see API errors without checking logs
- Non-blocking notifications
- Better user experience during connection issues

### 3. **Thread Management**
- ✅ Added `thread.join(timeout=5)` in `plugin_stop()`
- ✅ Proper shutdown sequence
- ✅ Prevents hanging during EDMC exit

**Benefits:**
- Cleaner shutdown
- Follows EDMC best practices
- Prevents potential issues

### 4. **API Compliance**
- ✅ Changed `config.get()` to `config.get_str()`
- ✅ Only using supported EDMC imports
- ✅ Proper logger setup with fallback
- ✅ Unique config key prefix ("ravencolonial_")

**Benefits:**
- Future-proof against EDMC updates
- No deprecated API usage
- Full compliance with plugin guidelines

## 📋 Pre-Release Tasks

### Testing
- [ ] Test language switching (if multiple languages available)
- [ ] Test error display (disconnect internet, trigger API error)
- [ ] Test plugin shutdown (check logs for clean exit)
- [ ] Test at construction ship (button states)
- [ ] Test project creation flow
- [ ] Test existing project detection

### Documentation
- [x] Updated CHANGELOG.md
- [x] Updated version to 1.3.0
- [x] Created L10n/en.template
- [ ] Update README.md with version info
- [ ] Add screenshots if UI changed significantly

### Distribution Prep
Files to include in .zip:
- ✅ `load.py`
- ✅ `README.md`
- ✅ `CHANGELOG.md`
- ✅ `L10n/en.template`

Files to EXCLUDE:
- ❌ `.git/` folder
- ❌ `.gitignore`
- ❌ `bounce.ps1`
- ❌ `LOGGING_CONVERSION.md`
- ❌ `requirements.txt` (requests is bundled with EDMC)
- ❌ `RELEASE_CHECKLIST.md` (this file)
- ❌ `__pycache__/` folder
- ❌ `.pyc` files

### Final Checks
- [ ] Plugin folder named `Ravencolonial-EDMC`
- [ ] No syntax errors in `load.py`
- [ ] All imports are from supported EDMC APIs
- [ ] Logger name is correct: `EDMarketConnector.Ravencolonial-EDMC`
- [ ] Version number matches in all docs

## 🎯 What's New for Users

### User-Facing Changes
1. **Multi-language ready** - UI can be translated to your language
2. **Better error visibility** - API errors show in main window
3. **Smoother shutdown** - No hanging when closing EDMC

### Technical Improvements
- Fully compliant with EDMC plugin API guidelines
- Better error handling and user feedback
- More maintainable codebase
- Ready for community translations

## 🌐 Future Translation Contributions

To add a translation:
1. Copy `L10n/en.template` to `L10n/<language_code>.strings`
2. Translate all strings (keep keys unchanged)
3. Test with EDMC language setting
4. Submit as pull request

Supported language codes: de, fr, es, ru, pl, pt, ja, zh-Hans, zh-Hant

## 📦 Distribution Command

To create release .zip:
```powershell
# From project root
Compress-Archive -Path load.py,README.md,CHANGELOG.md,L10n -DestinationPath Ravencolonial-EDMC-v1.3.0.zip
```

Then upload to GitHub releases!
