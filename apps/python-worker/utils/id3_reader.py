from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3, APIC
import os
import base64
from typing import Dict, Optional, Tuple
from io import BytesIO

def read_audio_metadata(file_path: str) -> Dict[str, Optional[str]]:
    """
    Read metadata from various audio file formats
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Dictionary containing metadata fields
    """
    metadata = {
        "title": None,
        "artist": None,
        "album": None,
        "date": None,
        "genre": None,
        "track": None,
        "albumartist": None,
        "duration": None,
        "has_artwork": False
    }
    
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.mp3':
            audio = MP3(file_path)
            tags = audio.tags
            
            if tags:
                # Title
                if 'TIT2' in tags:
                    metadata['title'] = str(tags['TIT2'])
                
                # Artist
                if 'TPE1' in tags:
                    metadata['artist'] = str(tags['TPE1'])
                elif 'TPE2' in tags:
                    metadata['artist'] = str(tags['TPE2'])
                
                # Album
                if 'TALB' in tags:
                    metadata['album'] = str(tags['TALB'])
                
                # Date/Year
                if 'TDRC' in tags:
                    metadata['date'] = str(tags['TDRC'])
                elif 'TYER' in tags:
                    metadata['date'] = str(tags['TYER'])
                
                # Genre
                if 'TCON' in tags:
                    metadata['genre'] = str(tags['TCON'])
                
                # Track number
                if 'TRCK' in tags:
                    metadata['track'] = str(tags['TRCK'])
                
                # Album artist
                if 'TPE2' in tags:
                    metadata['albumartist'] = str(tags['TPE2'])
                
                # Check for artwork
                for tag in tags.values():
                    if isinstance(tag, APIC):
                        metadata['has_artwork'] = True
                        break
            
            # Duration in seconds
            metadata['duration'] = audio.info.length
            
        elif ext in ['.m4a', '.mp4']:
            audio = MP4(file_path)
            tags = audio.tags
            
            if tags:
                # Title
                if '\xa9nam' in tags:
                    metadata['title'] = tags['\xa9nam'][0]
                
                # Artist
                if '\xa9ART' in tags:
                    metadata['artist'] = tags['\xa9ART'][0]
                
                # Album
                if '\xa9alb' in tags:
                    metadata['album'] = tags['\xa9alb'][0]
                
                # Date
                if '\xa9day' in tags:
                    metadata['date'] = tags['\xa9day'][0]
                
                # Genre
                if '\xa9gen' in tags:
                    metadata['genre'] = tags['\xa9gen'][0]
                
                # Track
                if 'trkn' in tags:
                    track_info = tags['trkn'][0]
                    if isinstance(track_info, tuple):
                        metadata['track'] = f"{track_info[0]}/{track_info[1]}" if len(track_info) > 1 else str(track_info[0])
                
                # Album artist
                if 'aART' in tags:
                    metadata['albumartist'] = tags['aART'][0]
                
                # Check for artwork
                if 'covr' in tags:
                    metadata['has_artwork'] = True
            
            metadata['duration'] = audio.info.length
            
        elif ext == '.flac':
            audio = FLAC(file_path)
            
            # FLAC uses Vorbis comments
            for key, tag_key in [
                ('title', 'title'),
                ('artist', 'artist'),
                ('album', 'album'),
                ('date', 'date'),
                ('genre', 'genre'),
                ('track', 'tracknumber'),
                ('albumartist', 'albumartist')
            ]:
                if tag_key in audio:
                    metadata[key] = audio[tag_key][0]
            
            # Check for artwork
            if audio.pictures:
                metadata['has_artwork'] = True
            
            metadata['duration'] = audio.info.length
            
        elif ext == '.ogg':
            audio = OggVorbis(file_path)
            
            # Ogg Vorbis also uses Vorbis comments
            for key, tag_key in [
                ('title', 'title'),
                ('artist', 'artist'),
                ('album', 'album'),
                ('date', 'date'),
                ('genre', 'genre'),
                ('track', 'tracknumber'),
                ('albumartist', 'albumartist')
            ]:
                if tag_key in audio:
                    metadata[key] = audio[tag_key][0]
            
            metadata['duration'] = audio.info.length
            
        # Clean up None values to empty strings for better display
        for key in metadata:
            if metadata[key] is None and key != 'has_artwork':
                metadata[key] = ""
                
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {str(e)}")
        # Return filename as title if we can't read metadata
        metadata['title'] = os.path.splitext(os.path.basename(file_path))[0]
    
    return metadata


def extract_artwork(file_path: str) -> Optional[Tuple[bytes, str]]:
    """
    Extract album artwork from audio file
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (image_data, mime_type) or None if no artwork found
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.mp3':
            audio = MP3(file_path)
            tags = audio.tags
            
            if tags:
                for tag in tags.values():
                    if isinstance(tag, APIC):
                        return (tag.data, tag.mime)
            
        elif ext in ['.m4a', '.mp4']:
            audio = MP4(file_path)
            tags = audio.tags
            
            if tags and 'covr' in tags:
                cover_list = tags['covr']
                if cover_list:
                    cover = cover_list[0]
                    # MP4 cover format: 0=None, 13=JPEG, 14=PNG
                    if cover.imageformat == 13:
                        return (bytes(cover), 'image/jpeg')
                    elif cover.imageformat == 14:
                        return (bytes(cover), 'image/png')
                    else:
                        # Default to JPEG if format unknown
                        return (bytes(cover), 'image/jpeg')
            
        elif ext == '.flac':
            audio = FLAC(file_path)
            
            if audio.pictures:
                picture = audio.pictures[0]
                return (picture.data, picture.mime)
            
    except Exception as e:
        print(f"Error extracting artwork from {file_path}: {str(e)}")
    
    return None 