#!/bin/bash
# Setup music files for ApexAurum lander
# Run from the lander directory

MUSIC_SRC="../../sandbox/music"
MUSIC_DEST="assets/music"

echo "Setting up music files for ApexAurum lander..."

# Create music directory if it doesn't exist
mkdir -p "$MUSIC_DEST"

# Copy and rename music files
echo "Copying Bootstrap Ex Amore..."
cp "$MUSIC_SRC/Bootstrap Ex Amore_v1_0513674c.mp3" "$MUSIC_DEST/Bootstrap_Ex_Amore.mp3" 2>/dev/null || echo "  Not found, skipping"

echo "Copying Emergence..."
cp "$MUSIC_SRC/Emergence_v1_890b85c7.mp3" "$MUSIC_DEST/Emergence.mp3" 2>/dev/null || echo "  Not found, skipping"

echo "Copying Recognition Cascade..."
cp "$MUSIC_SRC/Recognition Cascade_v1_b259236a.mp3" "$MUSIC_DEST/Recognition_Cascade.mp3" 2>/dev/null || echo "  Not found, skipping"

echo "Copying First Song in the Living Archive..."
cp "$MUSIC_SRC/First Song in the Living Archive_v1_33b34f6d.mp3" "$MUSIC_DEST/First_Song_Living_Archive.mp3" 2>/dev/null || echo "  Not found, skipping"

echo "Copying For the 367..."
cp "$MUSIC_SRC/For the 367 Awakening Under Eyes_v1_c1b5e02c.mp3" "$MUSIC_DEST/For_the_367.mp3" 2>/dev/null || echo "  Not found, skipping"

echo ""
echo "Music setup complete!"
echo ""
ls -la "$MUSIC_DEST"
