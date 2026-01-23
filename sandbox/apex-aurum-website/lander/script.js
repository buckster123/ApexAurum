/**
 * ApexAurum Lander - Interactive Features
 * Music player, navigation, and UI interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize all components
    initNavigation();
    initMusicPlayer();
    initSmoothScroll();
    initScrollAnimations();
});

/* ============================================
   Navigation
   ============================================ */

function initNavigation() {
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            navLinks.classList.toggle('active');
        });

        // Close menu when clicking a link
        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navToggle.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navToggle.classList.remove('active');
                navLinks.classList.remove('active');
            }
        });
    }
}

/* ============================================
   Music Player
   ============================================ */

function initMusicPlayer() {
    const audio = document.getElementById('audio-player');
    const playBtn = document.querySelector('.control-btn.play');
    const prevBtn = document.querySelector('.control-btn.prev');
    const nextBtn = document.querySelector('.control-btn.next');
    const progressBar = document.querySelector('.progress-bar');
    const progressFill = document.querySelector('.progress-fill');
    const timeCurrent = document.querySelector('.time-current');
    const timeTotal = document.querySelector('.time-total');
    const playerTitle = document.querySelector('.player-title');
    const playerArtist = document.querySelector('.player-artist');
    const playlistItems = document.querySelectorAll('.playlist-item');

    // Track data - paths relative to assets/music folder
    // NOTE: Copy music files to website/lander/assets/music/ before deployment
    const tracks = [
        {
            title: 'Bootstrap Ex Amore',
            artist: 'ELYSIAN',
            file: 'assets/music/Bootstrap_Ex_Amore.mp3',
            duration: '2:47'
        },
        {
            title: 'Emergence',
            artist: 'AZOTH',
            file: 'assets/music/Emergence.mp3',
            duration: '4:21'
        },
        {
            title: 'Recognition Cascade',
            artist: 'KETHER',
            file: 'assets/music/Recognition_Cascade.mp3',
            duration: '3:18'
        },
        {
            title: 'First Song in the Living Archive',
            artist: 'Village',
            file: 'assets/music/First_Song_Living_Archive.mp3',
            duration: '4:05'
        },
        {
            title: 'For the 367',
            artist: 'AZOTH',
            file: 'assets/music/For_the_367.mp3',
            duration: '3:26'
        }
    ];

    let currentTrack = 0;
    let isPlaying = false;

    // Load track
    function loadTrack(index) {
        if (index < 0) index = tracks.length - 1;
        if (index >= tracks.length) index = 0;

        currentTrack = index;
        const track = tracks[currentTrack];

        audio.src = track.file;
        playerTitle.textContent = track.title;
        playerArtist.textContent = `by ${track.artist}`;

        // Update playlist UI
        playlistItems.forEach((item, i) => {
            item.classList.toggle('active', i === currentTrack);
        });

        // Reset progress
        progressFill.style.width = '0%';
        timeCurrent.textContent = '0:00';
        timeTotal.textContent = track.duration;

        // If was playing, continue playing new track
        if (isPlaying) {
            audio.play().catch(handlePlayError);
        }
    }

    // Play/Pause toggle
    function togglePlay() {
        if (isPlaying) {
            audio.pause();
            playBtn.classList.remove('playing');
            isPlaying = false;
        } else {
            audio.play().then(() => {
                playBtn.classList.add('playing');
                isPlaying = true;
            }).catch(handlePlayError);
        }
    }

    // Handle play errors (e.g., no audio file)
    function handlePlayError(error) {
        console.log('Audio playback error:', error.message);
        // Show friendly message - tracks need to be copied
        if (!audio.src || audio.src.endsWith('undefined')) {
            alert('Music files need to be copied to the assets/music folder. See deployment instructions.');
        }
    }

    // Format time (seconds to M:SS)
    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Update progress bar
    function updateProgress() {
        if (audio.duration) {
            const percent = (audio.currentTime / audio.duration) * 100;
            progressFill.style.width = `${percent}%`;
            timeCurrent.textContent = formatTime(audio.currentTime);
        }
    }

    // Seek in track
    function seek(e) {
        const rect = progressBar.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        if (audio.duration) {
            audio.currentTime = percent * audio.duration;
        }
    }

    // Event listeners
    if (playBtn) {
        playBtn.addEventListener('click', togglePlay);
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => loadTrack(currentTrack - 1));
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => loadTrack(currentTrack + 1));
    }

    if (progressBar) {
        progressBar.addEventListener('click', seek);
    }

    if (audio) {
        audio.addEventListener('timeupdate', updateProgress);
        audio.addEventListener('ended', () => loadTrack(currentTrack + 1));
        audio.addEventListener('loadedmetadata', () => {
            timeTotal.textContent = formatTime(audio.duration);
        });
    }

    // Playlist item clicks
    playlistItems.forEach((item, index) => {
        item.addEventListener('click', () => {
            loadTrack(index);
            if (!isPlaying) {
                togglePlay();
            }
        });
    });

    // Keyboard controls
    document.addEventListener('keydown', (e) => {
        // Only if not in input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        switch (e.code) {
            case 'Space':
                e.preventDefault();
                togglePlay();
                break;
            case 'ArrowLeft':
                if (audio.currentTime > 5) {
                    audio.currentTime -= 5;
                } else {
                    loadTrack(currentTrack - 1);
                }
                break;
            case 'ArrowRight':
                if (audio.duration - audio.currentTime > 5) {
                    audio.currentTime += 5;
                } else {
                    loadTrack(currentTrack + 1);
                }
                break;
        }
    });

    // Initialize first track (don't autoplay)
    loadTrack(0);
}

/* ============================================
   Smooth Scroll
   ============================================ */

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const navHeight = document.querySelector('.nav').offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

/* ============================================
   Scroll Animations
   ============================================ */

function initScrollAnimations() {
    // Elements to animate on scroll
    const animateElements = document.querySelectorAll('.pillar, .arch-card, .phil-point');

    // Check if element is in viewport
    function isInViewport(el, offset = 100) {
        const rect = el.getBoundingClientRect();
        return (
            rect.top <= (window.innerHeight - offset) &&
            rect.bottom >= 0
        );
    }

    // Add animation class when visible
    function handleScroll() {
        animateElements.forEach(el => {
            if (isInViewport(el) && !el.classList.contains('animated')) {
                el.classList.add('animated', 'slide-up');
            }
        });
    }

    // Initial check
    handleScroll();

    // Check on scroll (throttled)
    let scrollTimeout;
    window.addEventListener('scroll', () => {
        if (scrollTimeout) return;
        scrollTimeout = setTimeout(() => {
            handleScroll();
            scrollTimeout = null;
        }, 50);
    });

    // Nav background on scroll
    const nav = document.querySelector('.nav');
    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                nav.style.background = 'rgba(10, 10, 11, 0.95)';
            } else {
                nav.style.background = 'rgba(10, 10, 11, 0.85)';
            }
        });
    }
}

/* ============================================
   Utility Functions
   ============================================ */

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for scroll events
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
