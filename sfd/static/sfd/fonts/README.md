# Fonts Directory

This directory contains font files used for PDF generation in the SFD project.

**Location**: `sfd/static/fonts/`

## Required Font Files

Place the following font files in this directory:

### IPA Fonts

- `ipaexm.ttf` - IPA exMincho (明朝体)
- `ipaexg.ttf` - IPA exGothic (ゴシック体)

### Noto Sans JP Fonts

- `NotoSansJP-Regular.ttf` - Regular weight
- `NotoSansJP-Bold.ttf` - Bold weight
- `NotoSansJP-ExtraBold.ttf` - Extra bold weight
- `NotoSansJP-Thin.ttf` - Thin weight
- `NotoSansJP-Light.ttf` - Light weight
- `NotoSansJP-ExtraLight.ttf` - Extra light weight

## Font Sources

### IPA Fonts

- Download from: <https://moji.or.jp/ipafont/>
- License: IPA Font License

### Noto Sans JP Fonts

- Download from: <https://fonts.google.com/noto/specimen/Noto+Sans+JP>
- License: SIL Open Font License

## Usage

These fonts are automatically registered by the `sfd.common.font.register_japanese_fonts()` function and used in PDF generation throughout the application.

## Production Deployment

### Font Collection for Production

Both IPA Fonts and Noto Sans JP fonts can be safely deployed in production environments:

- **IPA Fonts**: Licensed under IPA Font License (allows commercial use and redistribution)
- **Noto Sans JP**: Licensed under SIL Open Font License (fully open source)

### Deployment Options

1. **Static Files Collection** (Recommended)

   ```bash
   # Include fonts in static files
   python manage.py collectstatic
   ```

2. **Container Deployment**

   ```dockerfile
   # In Dockerfile
   COPY static/fonts/ /app/static/fonts/
   ```

3. **Automated Font Download**

   ```bash
   # Download fonts during deployment
   wget -O static/fonts/NotoSansJP-Regular.ttf "https://fonts.google.com/download?family=Noto%20Sans%20JP"
   ```

## Note

Font files are not included in the repository due to size and licensing considerations. Download and place them manually in this directory.
