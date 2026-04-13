# SESSION — 2026-04-13 19:37

## Проект
garcia

## Що зробили
fixed HEIC photo support in _paths_to_image_data: pillow-heif installed, convert HEIC/HEIF to JPEG before base64 encoding

## Наступний крок
no next step

## Контекст
Anthropic API returns 400 on HEIC even with image/jpeg mime_type; solution: pillow_heif.register_heif_opener + PIL convert RGB + save to BytesIO as JPEG
