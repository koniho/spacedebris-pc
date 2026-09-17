# Building Space Debris for macOS

## Prerequisites

- macOS 10.13+
- Python 3.8+
- PyInstaller: `pip install pyinstaller`
- PyQt5: `pip install PyQt5`

## Build Steps

### 1. Compile Qt Resources

```bash
cd /path/to/spacedebris-pc
pyrcc5 resources.qrc -o resources_rc.py
```

### 2. Build the App Bundle

```bash
pyinstaller space-debris-macos.spec
```

The app bundle will be created at `dist/Space Debris.app`.

### 3. Sign the App

**Ad-hoc signing (local testing only):**
```bash
codesign --force --deep --sign - "dist/Space Debris.app"
```

**With Developer ID (for distribution):**
```bash
codesign --force --deep --options runtime \
    --sign "Developer ID Application: Your Name (TEAMID)" \
    "dist/Space Debris.app"
```

### 4. Verify Signature

```bash
codesign --verify --verbose "dist/Space Debris.app"
```

---

## Getting an Apple Developer ID

### 1. Enroll in Apple Developer Program

1. Go to https://developer.apple.com/programs/enroll
2. Sign in with your Apple ID (or create one)
3. Pay the $99/year fee
4. Wait for approval (usually 24-48 hours)

### 2. Create Signing Certificates

**Option A: Via Xcode (easiest)**
```
Xcode → Settings → Accounts → Your Apple ID → Manage Certificates → + → Developer ID Application
```

**Option B: Via Apple Developer Portal**
1. Go to https://developer.apple.com/account/resources/certificates
2. Click + to create new certificate
3. Select "Developer ID Application" (for distributing outside App Store)
4. Follow the CSR (Certificate Signing Request) process
5. Download and double-click to install in Keychain

### 3. Find Your Signing Identity

```bash
security find-identity -v -p codesigning
```

Output looks like:
```
1) ABC123... "Developer ID Application: Your Name (TEAMID)"
```

Use the quoted string as your `--sign` argument.

---

## Notarization (Required for Distribution)

Notarization is required for apps distributed outside the Mac App Store on macOS 10.15+.

### 1. Create App-Specific Password

1. Go to https://appleid.apple.com
2. Sign In → Security → App-Specific Passwords → Generate
3. Save the password securely

### 2. Submit for Notarization

```bash
# Create ZIP for upload
ditto -c -k --keepParent "dist/Space Debris.app" "Space Debris.zip"

# Submit to Apple
xcrun notarytool submit "Space Debris.zip" \
    --apple-id "your@email.com" \
    --team-id "TEAMID" \
    --password "xxxx-xxxx-xxxx-xxxx" \
    --wait
```

### 3. Staple the Ticket

After notarization succeeds:
```bash
xcrun stapler staple "dist/Space Debris.app"
```

### 4. Verify Notarization

```bash
spctl --assess --verbose "dist/Space Debris.app"
```

---

## Creating a DMG for Distribution

```bash
# Install create-dmg via Homebrew
brew install create-dmg

# Create DMG
create-dmg \
    --volname "Space Debris" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Space Debris.app" 175 120 \
    --app-drop-link 425 120 \
    "Space Debris-1.0.0.dmg" \
    "dist/Space Debris.app"
```

---

## Troubleshooting

### "App is damaged and can't be opened"
The app isn't signed or notarized. For local testing:
```bash
xattr -cr "dist/Space Debris.app"
```

### "Unidentified developer" warning
You need a Developer ID certificate and proper signing. Ad-hoc signed apps will show this warning.

### Notarization fails
- Check hardened runtime is enabled (`--options runtime` in codesign)
- Ensure no unsigned binaries in the bundle
- Check Apple's notarization log for specific issues:
  ```bash
  xcrun notarytool log <submission-id> \
      --apple-id "your@email.com" \
      --team-id "TEAMID" \
      --password "xxxx-xxxx-xxxx-xxxx"
  ```
