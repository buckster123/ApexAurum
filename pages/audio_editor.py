"""
Audio Editor - Visual audio editing interface

Features:
- Waveform visualization with selection
- Trim, fade, normalize, loop, speed controls
- Real-time preview
- Non-destructive editing (keeps originals)
- Batch processing support
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.audio_editor import (
    audio_info,
    audio_trim,
    audio_fade,
    audio_normalize,
    audio_loop,
    audio_concat,
    audio_speed,
    audio_reverse,
    audio_list_files,
    audio_get_waveform,
)

# Page config
st.set_page_config(
    page_title="Audio Editor",
    page_icon="🎚️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stAudio {
        width: 100%;
    }
    .waveform-container {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
    }
    .operation-card {
        background: #1e1e1e;
        border-radius: 8px;
        padding: 15px;
        margin: 5px 0;
        border: 1px solid #333;
    }
    .success-box {
        background: #1a3d1a;
        border: 1px solid #2d5a2d;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px;
    }
    .info-item {
        background: #2a2a2a;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
    }
    .file-list-item {
        padding: 8px 12px;
        border-radius: 6px;
        margin: 4px 0;
        cursor: pointer;
        transition: background 0.2s;
    }
    .file-list-item:hover {
        background: #3a3a3a;
    }
</style>
""", unsafe_allow_html=True)


def render_waveform(waveform_data: list, duration: float, start_pct: float = 0, end_pct: float = 100):
    """Render waveform using Streamlit's bar chart with selection overlay"""
    import pandas as pd

    if not waveform_data:
        st.warning("No waveform data available")
        return

    # Create dataframe for visualization
    num_points = len(waveform_data)
    time_points = [i * duration / num_points for i in range(num_points)]

    # Create chart data
    df = pd.DataFrame({
        'Time (s)': time_points,
        'Amplitude': waveform_data
    })

    # Use area chart for waveform visualization
    st.area_chart(df.set_index('Time (s)'), height=150, use_container_width=True)


def format_time(seconds: float) -> str:
    """Format seconds as MM:SS.mmm"""
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:05.2f}"


def main():
    st.title("🎚️ Audio Editor")
    st.caption("Trim, fade, normalize, and process audio files")

    # Initialize session state
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = None
    if 'audio_info' not in st.session_state:
        st.session_state.audio_info = None
    if 'waveform' not in st.session_state:
        st.session_state.waveform = None
    if 'last_output' not in st.session_state:
        st.session_state.last_output = None

    # Sidebar - File Browser
    with st.sidebar:
        st.header("📁 Audio Files")

        # Folder selector
        folder_options = {
            "Music Library": "sandbox/music",
            "Edited Files": "sandbox/music/edited",
        }
        selected_folder = st.selectbox(
            "Folder",
            options=list(folder_options.keys()),
            key="folder_select"
        )
        folder_path = folder_options[selected_folder]

        # Refresh button
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

        # File list
        files_result = audio_list_files(folder_path)
        if files_result['success'] and files_result['files']:
            st.caption(f"{files_result['count']} files")

            for f in files_result['files']:
                col1, col2 = st.columns([3, 1])
                with col1:
                    # Truncate long names
                    display_name = f['name'][:25] + "..." if len(f['name']) > 28 else f['name']
                    if st.button(
                        f"🎵 {display_name}",
                        key=f"file_{f['name']}",
                        use_container_width=True,
                        help=f"{f['name']} ({f['size_mb']}MB)"
                    ):
                        st.session_state.selected_file = f['path']
                        st.session_state.audio_info = None
                        st.session_state.waveform = None
                        st.rerun()
                with col2:
                    st.caption(f"{f['size_mb']}MB")
        else:
            st.info("No audio files found")

        # Last output quick access
        if st.session_state.last_output:
            st.divider()
            st.subheader("📤 Last Output")
            if st.button("Load Last Output", use_container_width=True):
                st.session_state.selected_file = st.session_state.last_output
                st.session_state.audio_info = None
                st.session_state.waveform = None
                st.rerun()

    # Main content
    if st.session_state.selected_file:
        file_path = st.session_state.selected_file

        # Load audio info if not cached
        if st.session_state.audio_info is None:
            with st.spinner("Loading audio..."):
                st.session_state.audio_info = audio_info(file_path)
                wf = audio_get_waveform(file_path, num_points=300)
                if wf['success']:
                    st.session_state.waveform = wf

        info = st.session_state.audio_info
        waveform = st.session_state.waveform

        if not info.get('success'):
            st.error(f"Failed to load audio: {info.get('error')}")
            return

        # File header
        st.subheader(f"🎵 {Path(file_path).name}")

        # Audio player
        col1, col2 = st.columns([2, 1])
        with col1:
            st.audio(file_path)
        with col2:
            st.metric("Duration", info['duration_formatted'])

        # Info grid
        st.markdown("#### Audio Properties")
        cols = st.columns(5)
        with cols[0]:
            st.metric("Sample Rate", f"{info['sample_rate']}Hz")
        with cols[1]:
            st.metric("Channels", info['channels'])
        with cols[2]:
            st.metric("Volume", f"{info['dbfs']} dBFS")
        with cols[3]:
            st.metric("Size", f"{info['file_size_mb']}MB")
        with cols[4]:
            if 'estimated_bpm' in info:
                st.metric("Est. BPM", info['estimated_bpm'])

        # Waveform visualization
        if waveform and waveform.get('success'):
            st.markdown("#### Waveform")
            render_waveform(waveform['waveform'], info['duration_seconds'])

        st.divider()

        # Operations tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "✂️ Trim",
            "📈 Fade",
            "🔊 Normalize",
            "🔄 Loop/Speed",
            "📦 Batch"
        ])

        with tab1:
            st.markdown("### Trim Audio")
            st.caption("Cut audio to specific start and end times")

            col1, col2 = st.columns(2)
            with col1:
                start_time = st.number_input(
                    "Start Time (seconds)",
                    min_value=0.0,
                    max_value=float(info['duration_seconds']),
                    value=0.0,
                    step=0.1,
                    key="trim_start"
                )
            with col2:
                end_time = st.number_input(
                    "End Time (seconds)",
                    min_value=0.0,
                    max_value=float(info['duration_seconds']),
                    value=min(5.0, float(info['duration_seconds'])),
                    step=0.1,
                    key="trim_end"
                )

            # Preview duration
            trim_duration = end_time - start_time
            st.info(f"Output duration: {format_time(trim_duration)} ({trim_duration:.2f}s)")

            # Quick presets
            st.markdown("**Quick Presets:**")
            preset_cols = st.columns(5)
            with preset_cols[0]:
                if st.button("3s SFX", use_container_width=True):
                    st.session_state.trim_end = min(3.0, info['duration_seconds'])
                    st.rerun()
            with preset_cols[1]:
                if st.button("5s SFX", use_container_width=True):
                    st.session_state.trim_end = min(5.0, info['duration_seconds'])
                    st.rerun()
            with preset_cols[2]:
                if st.button("10s Clip", use_container_width=True):
                    st.session_state.trim_end = min(10.0, info['duration_seconds'])
                    st.rerun()
            with preset_cols[3]:
                if st.button("30s Loop", use_container_width=True):
                    st.session_state.trim_end = min(30.0, info['duration_seconds'])
                    st.rerun()
            with preset_cols[4]:
                if st.button("First Half", use_container_width=True):
                    st.session_state.trim_end = info['duration_seconds'] / 2
                    st.rerun()

            if st.button("✂️ Trim Audio", type="primary", use_container_width=True):
                with st.spinner("Trimming..."):
                    result = audio_trim(file_path, start=start_time, end=end_time)
                    if result['success']:
                        st.success(f"✅ Trimmed! Saved to: `{result['output_file']}`")
                        st.session_state.last_output = result['output_file']
                        st.audio(result['output_file'])
                    else:
                        st.error(f"Failed: {result['error']}")

        with tab2:
            st.markdown("### Fade In/Out")
            st.caption("Add smooth fade transitions")

            col1, col2 = st.columns(2)
            with col1:
                fade_in = st.slider(
                    "Fade In (ms)",
                    min_value=0,
                    max_value=5000,
                    value=100,
                    step=50,
                    key="fade_in"
                )
            with col2:
                fade_out = st.slider(
                    "Fade Out (ms)",
                    min_value=0,
                    max_value=5000,
                    value=500,
                    step=50,
                    key="fade_out"
                )

            if st.button("📈 Apply Fades", type="primary", use_container_width=True):
                with st.spinner("Applying fades..."):
                    result = audio_fade(file_path, fade_in_ms=fade_in, fade_out_ms=fade_out)
                    if result['success']:
                        st.success(f"✅ Fades applied! Saved to: `{result['output_file']}`")
                        st.session_state.last_output = result['output_file']
                        st.audio(result['output_file'])
                    else:
                        st.error(f"Failed: {result['error']}")

        with tab3:
            st.markdown("### Normalize Volume")
            st.caption("Adjust audio to a consistent volume level")

            current_vol = info['dbfs']
            st.info(f"Current volume: **{current_vol} dBFS**")

            target_dbfs = st.slider(
                "Target Volume (dBFS)",
                min_value=-30.0,
                max_value=0.0,
                value=-14.0,
                step=0.5,
                help="-14 dBFS is broadcast standard, -12 is louder"
            )

            gain = target_dbfs - current_vol
            if gain > 0:
                st.caption(f"Will boost by +{gain:.1f} dB")
            else:
                st.caption(f"Will reduce by {gain:.1f} dB")

            # Presets
            st.markdown("**Presets:**")
            preset_cols = st.columns(4)
            with preset_cols[0]:
                if st.button("Quiet (-20)", use_container_width=True):
                    st.session_state.target_vol = -20.0
            with preset_cols[1]:
                if st.button("Broadcast (-14)", use_container_width=True):
                    st.session_state.target_vol = -14.0
            with preset_cols[2]:
                if st.button("Loud (-10)", use_container_width=True):
                    st.session_state.target_vol = -10.0
            with preset_cols[3]:
                if st.button("Max (-3)", use_container_width=True):
                    st.session_state.target_vol = -3.0

            if st.button("🔊 Normalize", type="primary", use_container_width=True):
                with st.spinner("Normalizing..."):
                    result = audio_normalize(file_path, target_dbfs=target_dbfs)
                    if result['success']:
                        st.success(f"✅ Normalized! {result['original_dbfs']} → {result['final_dbfs']} dBFS")
                        st.session_state.last_output = result['output_file']
                        st.audio(result['output_file'])
                    else:
                        st.error(f"Failed: {result['error']}")

        with tab4:
            st.markdown("### Loop & Speed")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🔄 Create Loop")
                loop_count = st.number_input(
                    "Loop Count",
                    min_value=2,
                    max_value=10,
                    value=2,
                    help="Number of repetitions"
                )
                crossfade = st.slider(
                    "Crossfade (ms)",
                    min_value=0,
                    max_value=2000,
                    value=200,
                    step=50,
                    help="Overlap between loops for seamless transition"
                )

                estimated_duration = info['duration_seconds'] * loop_count - (crossfade/1000 * (loop_count-1))
                st.caption(f"Estimated output: {format_time(estimated_duration)}")

                if st.button("🔄 Create Loop", type="primary", use_container_width=True):
                    with st.spinner("Creating loop..."):
                        result = audio_loop(file_path, loop_count=loop_count, crossfade_ms=crossfade)
                        if result['success']:
                            st.success(f"✅ Loop created! Duration: {result['looped_duration_formatted']}")
                            st.session_state.last_output = result['output_file']
                            st.audio(result['output_file'])
                        else:
                            st.error(f"Failed: {result['error']}")

            with col2:
                st.markdown("#### ⏩ Change Speed")
                speed_factor = st.slider(
                    "Speed Factor",
                    min_value=0.5,
                    max_value=2.0,
                    value=1.0,
                    step=0.1,
                    help="0.5 = half speed, 2.0 = double speed"
                )
                preserve_pitch = st.checkbox("Preserve Pitch", value=True,
                    help="Keep pitch the same (time stretch) vs. chipmunk/slow-mo effect")

                new_duration = info['duration_seconds'] / speed_factor
                st.caption(f"New duration: {format_time(new_duration)}")

                if st.button("⏩ Change Speed", type="primary", use_container_width=True):
                    with st.spinner("Processing..."):
                        result = audio_speed(file_path, speed_factor=speed_factor, preserve_pitch=preserve_pitch)
                        if result['success']:
                            st.success(f"✅ Speed changed!")
                            st.session_state.last_output = result['output_file']
                            st.audio(result['output_file'])
                        else:
                            st.error(f"Failed: {result['error']}")

                st.divider()

                st.markdown("#### 🔀 Reverse")
                if st.button("🔀 Reverse Audio", use_container_width=True):
                    with st.spinner("Reversing..."):
                        result = audio_reverse(file_path)
                        if result['success']:
                            st.success(f"✅ Reversed!")
                            st.session_state.last_output = result['output_file']
                            st.audio(result['output_file'])
                        else:
                            st.error(f"Failed: {result['error']}")

        with tab5:
            st.markdown("### Batch Processing")
            st.caption("Process multiple files at once (coming soon)")

            st.info("🚧 Batch processing UI coming soon! For now, use the tools programmatically:\n\n```python\nfrom tools.audio_editor import audio_trim, audio_normalize\n\nfiles = ['file1.mp3', 'file2.mp3']\nfor f in files:\n    audio_trim(f, start=0, end=5)\n```")

            # Concatenate section
            st.markdown("#### 🔗 Concatenate Files")
            st.caption("Combine multiple audio files into one")

            concat_files = st.multiselect(
                "Select files to concatenate (in order)",
                options=[f['name'] for f in files_result.get('files', [])],
                key="concat_files"
            )

            if len(concat_files) >= 2:
                concat_crossfade = st.slider(
                    "Crossfade between files (ms)",
                    min_value=0,
                    max_value=2000,
                    value=100,
                    key="concat_crossfade"
                )

                if st.button("🔗 Concatenate", type="primary"):
                    with st.spinner("Concatenating..."):
                        # Resolve full paths
                        full_paths = [str(Path(folder_path) / f) for f in concat_files]
                        result = audio_concat(full_paths, crossfade_ms=concat_crossfade)
                        if result['success']:
                            st.success(f"✅ Concatenated {len(concat_files)} files!")
                            st.session_state.last_output = result['output_file']
                            st.audio(result['output_file'])
                        else:
                            st.error(f"Failed: {result['error']}")
            else:
                st.caption("Select at least 2 files to concatenate")

    else:
        # No file selected
        st.info("👈 Select an audio file from the sidebar to begin editing")

        # Quick stats
        st.markdown("### 📊 Library Stats")
        music_files = audio_list_files("sandbox/music")
        edited_files = audio_list_files("sandbox/music/edited")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Music Library", f"{music_files.get('count', 0)} files")
        with col2:
            st.metric("Edited Files", f"{edited_files.get('count', 0)} files")

        # Recent Village sounds
        if music_files.get('success'):
            village_files = [f for f in music_files['files'] if 'Village' in f['name'] or 'Agent' in f['name']]
            if village_files:
                st.markdown("### 🏘️ Village Sounds")
                for f in village_files[:6]:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.text(f['name'])
                    with col2:
                        st.caption(f"{f['size_mb']}MB")
                    with col3:
                        if st.button("Edit", key=f"quick_{f['name']}"):
                            st.session_state.selected_file = f['path']
                            st.rerun()


if __name__ == "__main__":
    main()
