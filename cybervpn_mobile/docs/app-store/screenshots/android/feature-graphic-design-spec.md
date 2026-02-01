# Feature Graphic Design Specification

## Overview
The feature graphic is a 1024 x 500 pixel banner displayed at the top of your Google Play Store listing. It's one of the most important visual elements for attracting users.

## Exact Requirements

- **Dimensions**: Exactly 1024 x 500 pixels
- **Format**: PNG or JPEG (24-bit RGB)
- **Alpha Channel**: Not allowed (must be opaque)
- **Color Space**: sRGB
- **File Size**: Keep under 1MB for fast loading

## Safe Zone

Keep all important text and imagery within the safe zone to ensure visibility across all devices:

```
┌─────────────────────────────────────────────────────────────┐
│ ← 64px →                                         ← 64px →   │
│ ↑                                                           │
│ 64px                    SAFE ZONE                           │
│ ↓                                                           │
│         [All important content goes here]                   │
│ ↑                                                           │
│ 64px                                                        │
│ ↓                                                           │
└─────────────────────────────────────────────────────────────┘
           1024 x 500 pixels total
```

## Design Layout

### Recommended Layout Structure

```
┌───────────────────────────────────────────────────────────┐
│                                                           │
│  [APP ICON]     CYBERVPN                                  │
│   120x120                                                 │
│                 Secure. Anonymous. Fast.                  │
│                                                           │
│                 Military-Grade VPN Protection             │
│                                              [3D GLOBE/   │
│                                               NETWORK     │
│                                               VISUAL]     │
└───────────────────────────────────────────────────────────┘
```

### Element Breakdown

#### 1. App Icon (Left Side)
- **Position**: 80px from left edge, vertically centered
- **Size**: 120 x 120 pixels
- **Source**: `assets/images/app_icon.png`
- **Effect**: Optional subtle glow in matrix green

#### 2. App Name (Center-Left)
- **Text**: "CYBERVPN"
- **Font**: Orbitron Bold
- **Size**: 48px
- **Color**: #00FF88 (matrix green)
- **Position**: 220px from left edge, upper third
- **Effect**: Neon glow effect

#### 3. Tagline (Below App Name)
- **Text**: "Secure. Anonymous. Fast."
- **Font**: Orbitron Medium
- **Size**: 24px
- **Color**: #00FFFF (neon cyan)
- **Position**: Below app name with 12px spacing
- **Effect**: Subtle glow

#### 4. Subtitle (Below Tagline)
- **Text**: "Military-Grade VPN Protection"
- **Font**: System font (Roboto Regular)
- **Size**: 16px
- **Color**: #FFFFFF at 80% opacity
- **Position**: Below tagline with 8px spacing

#### 5. Visual Element (Right Side)
- **Type**: 3D globe or network visualization
- **Position**: Right side, 64px from right edge
- **Size**: ~400 x 400 pixels
- **Source**: Screenshot from app or custom 3D render
- **Effects**:
  - Neon glow on network lines
  - Matrix green particles
  - Cyberpunk aesthetic
  - Transparent or integrated into background

### Background

#### Option 1: Gradient Background
- **Type**: Diagonal gradient
- **Colors**:
  - Top-left: #0A0E1A (deep navy)
  - Bottom-right: #111827 (dark background)
- **Overlay**: Subtle scanline effect at 10% opacity

#### Option 2: Solid with Effects
- **Base Color**: #0A0E1A (deep navy)
- **Effects**:
  - Scanline overlay (horizontal lines, 2px spacing, 8% opacity)
  - Vignette effect on edges
  - Subtle matrix code rain in background (very faint)

## Typography Specifications

### Orbitron Font
- **Download**: [Google Fonts - Orbitron](https://fonts.google.com/specimen/Orbitron)
- **Weights to use**:
  - Bold (700) for "CYBERVPN"
  - Medium (500) for tagline
- **Letter Spacing**: +1.2px for cyberpunk aesthetic

### System Font (Roboto)
- Included with most design tools
- Regular (400) weight for subtitle
- Normal letter spacing

## Color Palette

```
Primary Colors:
- Matrix Green:  #00FF88  (RGB: 0, 255, 136)
- Neon Cyan:     #00FFFF  (RGB: 0, 255, 255)
- Neon Pink:     #FF00FF  (RGB: 255, 0, 255)

Background Colors:
- Deep Navy:     #0A0E1A  (RGB: 10, 14, 26)
- Dark BG:       #111827  (RGB: 17, 24, 39)

Neutral Colors:
- White:         #FFFFFF  (RGB: 255, 255, 255)
- Gray:          #6B7280  (RGB: 107, 114, 128)
```

## Glow Effects

### Text Glow
```css
/* For "CYBERVPN" title */
text-shadow:
  0 0 10px rgba(0, 255, 136, 0.8),
  0 0 20px rgba(0, 255, 136, 0.5),
  0 0 30px rgba(0, 255, 136, 0.3);

/* For tagline */
text-shadow:
  0 0 8px rgba(0, 255, 255, 0.6),
  0 0 16px rgba(0, 255, 255, 0.4);
```

### Visual Element Glow
- Use outer glow with matrix green color
- Blur: 12-16px
- Opacity: 40-60%
- Multiple layers for depth

## Design Tools & Templates

### Recommended Tools
1. **Figma** (Free, web-based)
   - Start with 1024 x 500 frame
   - Use auto-layout for responsive elements
   - Export as PNG at 2x for crisp quality

2. **Adobe Photoshop**
   - Create new document: 1024 x 500, 72 DPI, RGB
   - Use layer effects for glows
   - Save for web (PNG-24)

3. **GIMP** (Free alternative)
   - Same dimensions and settings as Photoshop
   - Use filters > Light and Shadow > Glow for effects

4. **Canva** (Easiest, web-based)
   - Custom dimensions: 1024 x 500
   - Limited effects but user-friendly

### Template Checklist

- [ ] Canvas is exactly 1024 x 500 pixels
- [ ] Background uses cyberpunk color scheme
- [ ] App icon is included (120 x 120 px)
- [ ] App name "CYBERVPN" in Orbitron Bold, 48px, matrix green
- [ ] Tagline in Orbitron Medium, 24px, neon cyan
- [ ] Subtitle in Roboto Regular, 16px, white 80% opacity
- [ ] Visual element (globe/network) on right side
- [ ] Neon glow effects applied to text
- [ ] All important content within 64px safe zone
- [ ] No alpha channel (fully opaque)
- [ ] Exported as PNG-24 or JPEG
- [ ] File size under 1MB

## Visual References

### Similar Styles
- Cyberpunk 2077 UI design
- Tron Legacy aesthetics
- Matrix movie interface
- Neon noir themes

### Key Characteristics
- High contrast between dark background and neon accents
- Glowing edges and text
- Futuristic typography
- 3D/depth perception
- Tech-inspired visuals (grids, networks, data streams)

## Testing Checklist

Before uploading to Google Play Console:

- [ ] Open image at 100% zoom - text is crisp and readable
- [ ] View at 50% zoom (thumbnail size) - still legible
- [ ] Check on dark theme display
- [ ] Check on light theme display
- [ ] Verify no transparency (no alpha channel)
- [ ] Confirm exact dimensions (1024 x 500)
- [ ] File format is PNG or JPEG
- [ ] Colors use sRGB color space
- [ ] Text has sufficient contrast with background
- [ ] No important content cut off at edges

## Example Workflow

1. **Set up canvas**
   - Create 1024 x 500 px document
   - Fill background with gradient (#0A0E1A to #111827)

2. **Add safe zone guides**
   - Draw guides at 64px from each edge

3. **Place app icon**
   - Import app icon (120 x 120)
   - Position at 80px from left, vertically centered

4. **Add text layers**
   - "CYBERVPN" - Orbitron Bold 48px, #00FF88
   - "Secure. Anonymous. Fast." - Orbitron Medium 24px, #00FFFF
   - "Military-Grade VPN Protection" - Roboto 16px, #FFFFFF 80%

5. **Apply glow effects**
   - Add outer glow to title (matrix green)
   - Add subtle glow to tagline (neon cyan)

6. **Add visual element**
   - Place 3D globe or network visual on right side
   - Apply glow and effects
   - Blend with background

7. **Add scanline overlay**
   - Create pattern of 2px horizontal lines
   - Set to 8-10% opacity
   - Cover entire canvas

8. **Final touches**
   - Adjust contrast and brightness
   - Fine-tune glow effects
   - Check safe zones

9. **Export**
   - Save as PNG-24 (no transparency)
   - Verify dimensions: 1024 x 500
   - Optimize file size if needed

## Approval Criteria

Google Play will reject feature graphics that:
- Have incorrect dimensions
- Include alpha transparency
- Have text smaller than 12pt
- Are blurry or low quality
- Violate content policies
- Are misleading about app functionality

Ensure your design:
- Accurately represents the app
- Follows Google Play design guidelines
- Has high contrast and readability
- Uses proper dimensions and format
- Contains no prohibited content
