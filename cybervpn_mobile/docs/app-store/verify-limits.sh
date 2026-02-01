#!/bin/bash
echo "Verifying App Store metadata character limits..."
echo ""

# English metadata
echo "=== ENGLISH METADATA ==="
app_name=$(jq -r '.app_store_ios.app_name' store-metadata-en.json)
subtitle=$(jq -r '.app_store_ios.subtitle' store-metadata-en.json)
description=$(jq -r '.app_store_ios.description' store-metadata-en.json)
keywords=$(jq -r '.app_store_ios.keywords' store-metadata-en.json)
short_desc=$(jq -r '.google_play.short_description' store-metadata-en.json)

echo "iOS App Name: ${#app_name} chars (limit: 30) - $app_name"
echo "iOS Subtitle: ${#subtitle} chars (limit: 30) - $subtitle"
echo "iOS Description: ${#description} chars (limit: 4000)"
echo "iOS Keywords: ${#keywords} chars (limit: 100) - $keywords"
echo ""
echo "Google Play App Name: ${#app_name} chars (limit: 30)"
echo "Google Play Short Desc: ${#short_desc} chars (limit: 80) - $short_desc"
echo ""

# Russian metadata
echo "=== RUSSIAN METADATA ==="
app_name_ru=$(jq -r '.app_store_ios.app_name' store-metadata-ru.json)
subtitle_ru=$(jq -r '.app_store_ios.subtitle' store-metadata-ru.json)
description_ru=$(jq -r '.app_store_ios.description' store-metadata-ru.json)
keywords_ru=$(jq -r '.app_store_ios.keywords' store-metadata-ru.json)
short_desc_ru=$(jq -r '.google_play.short_description' store-metadata-ru.json)

echo "iOS App Name: ${#app_name_ru} chars (limit: 30) - $app_name_ru"
echo "iOS Subtitle: ${#subtitle_ru} chars (limit: 30) - $subtitle_ru"
echo "iOS Description: ${#description_ru} chars (limit: 4000)"
echo "iOS Keywords: ${#keywords_ru} chars (limit: 100) - $keywords_ru"
echo ""
echo "Google Play App Name: ${#app_name_ru} chars (limit: 30)"
echo "Google Play Short Desc: ${#short_desc_ru} chars (limit: 80) - $short_desc_ru"
echo ""

# Check if any limits exceeded
errors=0
if [ ${#app_name} -gt 30 ]; then echo "ERROR: EN App Name exceeds 30 chars"; errors=$((errors+1)); fi
if [ ${#subtitle} -gt 30 ]; then echo "ERROR: EN Subtitle exceeds 30 chars"; errors=$((errors+1)); fi
if [ ${#description} -gt 4000 ]; then echo "ERROR: EN Description exceeds 4000 chars"; errors=$((errors+1)); fi
if [ ${#keywords} -gt 100 ]; then echo "ERROR: EN Keywords exceed 100 chars"; errors=$((errors+1)); fi
if [ ${#short_desc} -gt 80 ]; then echo "ERROR: EN Short Desc exceeds 80 chars"; errors=$((errors+1)); fi

if [ ${#app_name_ru} -gt 30 ]; then echo "ERROR: RU App Name exceeds 30 chars"; errors=$((errors+1)); fi
if [ ${#subtitle_ru} -gt 30 ]; then echo "ERROR: RU Subtitle exceeds 30 chars"; errors=$((errors+1)); fi
if [ ${#description_ru} -gt 4000 ]; then echo "ERROR: RU Description exceeds 4000 chars"; errors=$((errors+1)); fi
if [ ${#keywords_ru} -gt 100 ]; then echo "ERROR: RU Keywords exceed 100 chars"; errors=$((errors+1)); fi
if [ ${#short_desc_ru} -gt 80 ]; then echo "ERROR: RU Short Desc exceeds 80 chars"; errors=$((errors+1)); fi

if [ $errors -eq 0 ]; then
  echo "✓ All character limits are within acceptable ranges"
  exit 0
else
  echo "✗ Found $errors limit violations"
  exit 1
fi
