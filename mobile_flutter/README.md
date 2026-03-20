# GPS Tracker Mobile

Flutter mobile client for the GPS tracker system.

## Release packaging

1. Install Flutter and Android toolchain, then run:

```bash
flutter pub get
flutter doctor
```

2. Configure the backend address for the package build.

- Emulator debug default: `http://10.0.2.2:8000`
- Physical device or formal release: pass `--dart-define=API_BASE_URL=http://<server-ip>:8000`
- If your backend supports HTTPS, use `https://...` instead of HTTP.

3. Create a signing file for release packaging.

- Copy `android/key.properties.example` to `android/key.properties`
- Fill in your real keystore path, alias, and passwords
- `android/key.properties` is already ignored by git

Example:

```properties
storePassword=your-store-password
keyPassword=your-key-password
keyAlias=upload
storeFile=../keystore/upload-keystore.jks
```

4. Build the APK.

```bash
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.1.10:8000
```

Output file:

```text
build/app/outputs/flutter-apk/app-release.apk
```

## Notes

- Android release now includes `INTERNET` permission in the main manifest.
- `android:usesCleartextTraffic="true"` is enabled so LAN `http://` backends can be used during private deployment.
- If `android/key.properties` is missing, Gradle falls back to the debug signing key. That is only suitable for internal testing, not store distribution.
