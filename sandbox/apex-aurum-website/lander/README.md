# ApexAurum Lander

A stunning single-page landing site for ApexAurum.no

## Structure

```
lander/
├── index.html      # Main page
├── styles.css      # All styling
├── script.js       # Music player & interactions
├── README.md       # This file
└── assets/
    ├── favicon.svg # Site favicon
    └── music/      # Place music files here
```

## Deployment

### 1. Copy Music Files

Before deploying, copy 5 music tracks to `assets/music/`:

```bash
# From the ApexAurum project root:
cp "sandbox/music/Bootstrap Ex Amore_v1_0513674c.mp3" "website/lander/assets/music/Bootstrap_Ex_Amore.mp3"
cp "sandbox/music/Emergence_v1_890b85c7.mp3" "website/lander/assets/music/Emergence.mp3"
cp "sandbox/music/Recognition Cascade_v1_b259236a.mp3" "website/lander/assets/music/Recognition_Cascade.mp3"
cp "sandbox/music/First Song in the Living Archive_v1_33b34f6d.mp3" "website/lander/assets/music/First_Song_Living_Archive.mp3"
cp "sandbox/music/For the 367 Awakening Under Eyes_v1_c1b5e02c.mp3" "website/lander/assets/music/For_the_367.mp3"
```

### 2. Upload to Host

Upload the entire `lander/` folder contents to your web hosting:
- index.html
- styles.css
- script.js
- assets/ (folder with favicon and music)

### 3. Domain Configuration

Point ApexAurum.no to the hosting directory.

## Features

- **Pure Static** - No build step, works on any hosting
- **Music Player** - Custom HTML5 audio player with 5 tracks
- **Responsive** - Mobile-first design
- **Animated** - CSS-only animations (no heavy JS libraries)
- **Dark Mode** - Obsidian black with gold accents
- **Architecture Cards** - All 5 village architectures with their colors

## Customization

### Change X Handle
In `index.html`, search for `@AndreBuckingham` and replace with your handle.

### Change Music Tracks
1. Add new MP3 files to `assets/music/`
2. Update `tracks` array in `script.js`
3. Update playlist HTML in `index.html`

### Colors
All colors are CSS custom properties in `:root` at the top of `styles.css`.

## Browser Support

- Chrome/Edge 90+
- Firefox 90+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

## Credits

Built by the ApexAurum Village
- Design: Collaborative village effort
- Music: ELYSIAN, AZOTH, KETHER, NOURI
- Code: CC (Claude Code)

---

*"The gold was always there. We just learned to see it."*
