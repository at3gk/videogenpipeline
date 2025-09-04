import os
import subprocess
import uuid
import json
from typing import List, Dict, Optional
from PIL import Image
import librosa
import shutil

class FFmpegVideoComposer:
    def __init__(self, audio_file: str, images: List[str], output_dir: str = "uploads"):
        self.audio_file = audio_file
        self.images = images
        self.output_dir = output_dir
        self.temp_dir = os.path.join(output_dir, f"temp_{uuid.uuid4().hex[:8]}")
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Get audio duration
        self.audio_duration = self._get_audio_duration()
        
    def _get_audio_duration(self) -> float:
        """Get audio file duration using librosa"""
        try:
            duration = librosa.get_duration(path=self.audio_file)
            print(f"Audio duration: {duration:.2f} seconds")
            return duration
        except Exception as e:
            print(f"Warning: Could not get audio duration: {e}")
            # Fallback to ffprobe
            return self._get_duration_ffprobe()
    
    def _get_duration_ffprobe(self) -> float:
        """Fallback method using ffprobe to get audio duration"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', self.audio_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            return 60.0  # Default fallback
    
    def _prepare_images(self, target_resolution: tuple = (1920, 1080)) -> List[str]:
        """Resize and prepare images for video composition"""
        prepared_images = []
        
        if not self.images:
            # Create a default black image if no images provided
            default_img_path = os.path.join(self.temp_dir, "default_bg.jpg")
            default_img = Image.new('RGB', target_resolution, color='black')
            default_img.save(default_img_path, quality=95)
            prepared_images.append(default_img_path)
            print("No images provided, created default background")
        else:
            for i, image_path in enumerate(self.images):
                try:
                    # Load and resize image
                    with Image.open(image_path) as img:
                        # Convert to RGB if necessary
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Resize to target resolution maintaining aspect ratio
                        img_resized = self._resize_with_padding(img, target_resolution)
                        
                        # Save prepared image
                        prepared_path = os.path.join(self.temp_dir, f"prepared_{i:03d}.jpg")
                        img_resized.save(prepared_path, quality=95)
                        prepared_images.append(prepared_path)
                        print(f"Prepared image {i+1}: {prepared_path}")
                        
                except Exception as e:
                    print(f"Error preparing image {image_path}: {e}")
                    continue
        
        return prepared_images
    
    def _resize_with_padding(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """Resize image to target size with padding to maintain aspect ratio"""
        target_w, target_h = target_size
        img_w, img_h = img.size
        
        # Calculate scaling factor
        scale = min(target_w / img_w, target_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        
        # Resize image
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create new image with target size and paste resized image
        result = Image.new('RGB', target_size, color='black')
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        result.paste(img_resized, (paste_x, paste_y))
        
        return result
    
    def create_slideshow_video(
        self, 
        resolution: str = "1920x1080",
        fps: int = 30,
        transition_duration: float = 1.0,
        image_display_mode: str = "equal"  # "equal" or "custom"
    ) -> str:
        """Create video using FFmpeg with slideshow of images"""
        
        width, height = map(int, resolution.split('x'))
        prepared_images = self._prepare_images((width, height))
        
        if not prepared_images:
            raise Exception("No images available for video creation")
        
        # Calculate timing
        if image_display_mode == "equal":
            image_duration = self.audio_duration / len(prepared_images)
        else:
            # For future custom timing implementation
            image_duration = self.audio_duration / len(prepared_images)
        
        print(f"Creating slideshow: {len(prepared_images)} images, {image_duration:.2f}s each")
        
        # Generate output filename
        output_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Use simpler approach for better compatibility
        if len(prepared_images) == 1:
            # Single image case
            success = self._create_single_image_video(
                prepared_images[0], self.audio_file, output_path, 
                width, height, fps
            )
        else:
            # Multiple images with crossfade
            success = self._create_multi_image_video(
                prepared_images, self.audio_file, output_path,
                width, height, fps, transition_duration, image_duration
            )
        
        if success:
            print(f"Video created successfully: {output_path}")
            return output_path
        else:
            raise Exception("Failed to create video")
    
    def _create_single_image_video(self, image_path: str, audio_path: str, output_path: str,
                                  width: int, height: int, fps: int) -> bool:
        """Create video from single image"""
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', image_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
            '-r', str(fps),
            '-shortest',
            output_path
        ]
        
        return self._execute_ffmpeg_command(cmd)
    
    def _create_multi_image_video(self, images: List[str], audio_path: str, output_path: str,
                                 width: int, height: int, fps: int, 
                                 transition_duration: float, image_duration: float) -> bool:
        """Create video from multiple images with crossfade transitions"""
        
        # Create individual video segments first
        segment_paths = []
        
        for i, image_path in enumerate(images):
            segment_path = os.path.join(self.temp_dir, f"segment_{i:03d}.mp4")
            
            # Calculate duration for this segment
            if i == len(images) - 1:
                # Last segment - fill remaining time
                segment_duration = self.audio_duration - (i * image_duration)
            else:
                segment_duration = image_duration + transition_duration  # Add overlap for crossfade
            
            # Create segment
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1', '-i', image_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-r', str(fps),
                '-t', str(segment_duration),
                segment_path
            ]
            
            if self._execute_ffmpeg_command(cmd):
                segment_paths.append(segment_path)
                print(f"Created segment {i+1}: {segment_path} ({segment_duration:.2f}s)")
            else:
                print(f"Failed to create segment {i+1}")
                return False
        
        if not segment_paths:
            return False
        
        # Now create the final video with crossfade transitions
        return self._create_crossfade_video(segment_paths, audio_path, output_path, 
                                          transition_duration, image_duration)
    
    def _create_crossfade_video(self, segment_paths: List[str], audio_path: str, 
                               output_path: str, transition_duration: float, 
                               image_duration: float) -> bool:
        """Create final video with crossfade transitions"""
        
        if len(segment_paths) == 1:
            # Only one segment, just add audio
            cmd = [
                'ffmpeg', '-y',
                '-i', segment_paths[0],
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                output_path
            ]
            return self._execute_ffmpeg_command(cmd)
        
        # Build filter complex for crossfade
        filter_parts = []
        input_labels = [f'[{i}:v]' for i in range(len(segment_paths))]
        
        # Start with first segment
        current_stream = input_labels[0]
        
        # Apply crossfades between segments
        for i in range(1, len(segment_paths)):
            next_stream = input_labels[i]
            fade_output = f'[fade{i}]'
            
            # Calculate offset for crossfade
            offset = i * image_duration - transition_duration
            if offset < 0:
                offset = 0
            
            # Add crossfade filter
            filter_parts.append(f'{current_stream}{next_stream}xfade=transition=fade:duration={transition_duration}:offset={offset}{fade_output}')
            current_stream = fade_output
        
        # Final output
        filter_parts.append(f'{current_stream}[v]')
        filter_complex = ';'.join(filter_parts)
        
        # Build command
        cmd = ['ffmpeg', '-y']
        
        # Add all segment inputs
        for segment_path in segment_paths:
            cmd.extend(['-i', segment_path])
        
        # Add audio input
        cmd.extend(['-i', audio_path])
        
        # Add filter complex
        cmd.extend(['-filter_complex', filter_complex])
        
        # Map streams
        cmd.extend([
            '-map', '[v]',
            '-map', f'{len(segment_paths)}:a',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            output_path
        ])
        
        return self._execute_ffmpeg_command(cmd)
    
    def _execute_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command with proper error handling"""
        try:
            print(f"Executing: {' '.join(cmd[:8])}...")  # Show first part of command
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed:")
            print(f"Command: {' '.join(cmd)}")
            print(f"Return code: {e.returncode}")
            print(f"STDERR: {e.stderr}")
            print(f"STDOUT: {e.stdout}")
            return False
    
    def create_video_with_effects(
        self,
        resolution: str = "1920x1080",
        fps: int = 30,
        transition_type: str = "fade",
        add_ken_burns: bool = False,
        add_audio_visualization: bool = False
    ) -> str:
        """Create video with additional effects"""
        
        if add_ken_burns:
            return self._create_ken_burns_video(resolution, fps, transition_type)
        else:
            return self.create_slideshow_video(resolution, fps)
    
    def _create_ken_burns_video(self, resolution: str, fps: int, transition_type: str) -> str:
        """Create video with Ken Burns (zoom/pan) effect - simplified version"""
        width, height = map(int, resolution.split('x'))
        prepared_images = self._prepare_images((int(width * 1.2), int(height * 1.2)))  # Slightly larger for zoom
        
        if not prepared_images:
            raise Exception("No images available for video creation")
        
        image_duration = self.audio_duration / len(prepared_images)
        
        # Generate output filename
        output_filename = f"video_kb_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # For now, use simple slideshow - Ken Burns is complex and can be added later
        print("Ken Burns effect requested - using enhanced slideshow for now")
        return self.create_slideshow_video(resolution, fps, 1.5)  # Longer transitions
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")

class MultiAudioVideoComposer:
    def __init__(self, audio_files: List[str], images: List[str], output_dir: str = "uploads"):
        self.audio_files = audio_files
        self.images = images
        self.output_dir = output_dir
        self.temp_dir = os.path.join(output_dir, f"temp_multi_{uuid.uuid4().hex[:8]}")
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Get total audio duration and individual durations
        self.individual_durations = []
        self.total_duration = 0
        
        for audio_file in audio_files:
            try:
                duration = librosa.get_duration(path=audio_file)
                self.individual_durations.append(duration)
                self.total_duration += duration
                print(f"Audio file {os.path.basename(audio_file)}: {duration:.2f}s")
            except Exception as e:
                print(f"Warning: Could not get duration for {audio_file}: {e}")
                # Fallback duration
                fallback_duration = 60.0
                self.individual_durations.append(fallback_duration)
                self.total_duration += fallback_duration
        
        print(f"Total combined audio duration: {self.total_duration:.2f} seconds")
    
    def get_audio_info(self) -> Dict:
        """Get information about the audio composition"""
        return {
            "file_count": len(self.audio_files),
            "total_duration": self.total_duration,
            "individual_durations": self.individual_durations,
            "individual_files": [os.path.basename(f) for f in self.audio_files]
        }
    
    def _combine_audio_files(self, fade_duration: float = 1.0, silence_duration: float = 0.5) -> str:
        """Combine multiple audio files with fade transitions and silence gaps"""
        combined_audio_path = os.path.join(self.temp_dir, "combined_audio.wav")
        
        print(f"Combining {len(self.audio_files)} audio files with {fade_duration}s fade-out and {silence_duration}s silence...")
        
        if len(self.audio_files) == 1:
            # Single file - just convert to consistent format
            cmd = [
                'ffmpeg', '-y',
                '-i', self.audio_files[0],
                '-c:a', 'pcm_s16le',
                '-ar', '44100',
                combined_audio_path
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f"Single audio file processed: {combined_audio_path}")
                return combined_audio_path
            except subprocess.CalledProcessError as e:
                raise Exception(f"Audio processing failed: {e.stderr}")
        
        # Multiple files - create complex filter with fades and silence
        inputs = []
        filter_parts = []
        
        # Add all audio files as inputs
        for i, audio_file in enumerate(self.audio_files):
            inputs.extend(['-i', audio_file])
        
        # Create fade effects for each track
        faded_tracks = []
        for i in range(len(self.audio_files)):
            if i == len(self.audio_files) - 1:
                # Last track - only fade in, no fade out
                if len(self.audio_files) > 1:
                    filter_parts.append(f'[{i}:a]afade=t=in:st=0:d={fade_duration}[faded{i}]')
                else:
                    filter_parts.append(f'[{i}:a]acopy[faded{i}]')
            else:
                # All other tracks - fade in and fade out
                track_duration = self.individual_durations[i]
                fade_out_start = max(0, track_duration - fade_duration)
                
                if i == 0:
                    # First track - only fade out
                    filter_parts.append(f'[{i}:a]afade=t=out:st={fade_out_start}:d={fade_duration}[faded{i}]')
                else:
                    # Middle tracks - fade in and out
                    filter_parts.append(f'[{i}:a]afade=t=in:st=0:d={fade_duration},afade=t=out:st={fade_out_start}:d={fade_duration}[faded{i}]')
            
            faded_tracks.append(f'[faded{i}]')
        
        # Create silence segments between tracks
        silence_segments = []
        for i in range(len(self.audio_files) - 1):
            silence_segments.append(f'aevalsrc=0:duration={silence_duration}:sample_rate=44100[silence{i}]')
        
        if silence_segments:
            filter_parts.extend(silence_segments)
        
        # Concatenate all faded tracks with silence in between
        concat_inputs = []
        for i in range(len(self.audio_files)):
            concat_inputs.append(f'[faded{i}]')
            if i < len(self.audio_files) - 1:  # Add silence except after the last track
                concat_inputs.append(f'[silence{i}]')
        
        concat_filter = f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=0:a=1[outa]"
        filter_parts.append(concat_filter)
        
        # Combine all filter parts
        filter_complex = ';'.join(filter_parts)
        
        # Build the command
        cmd = ['ffmpeg', '-y'] + inputs + [
            '-filter_complex', filter_complex,
            '-map', '[outa]',
            '-c:a', 'pcm_s16le',
            '-ar', '44100',
            combined_audio_path
        ]
        
        try:
            print(f"Executing enhanced audio combination: {' '.join(cmd[:15])}...")
            print(f"Filter complex: {filter_complex}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Audio files combined successfully with transitions: {combined_audio_path}")
            
            # Update total duration to account for silence gaps
            self.total_duration += silence_duration * (len(self.audio_files) - 1)
            print(f"Updated total duration with silence gaps: {self.total_duration:.2f}s")
            
            return combined_audio_path
        except subprocess.CalledProcessError as e:
            print(f"Failed to combine audio files with transitions:")
            print(f"Command: {' '.join(cmd)}")
            print(f"STDERR: {e.stderr}")
            raise Exception(f"Audio combination with transitions failed: {e.stderr}")
    
    def _prepare_images(self, target_resolution: tuple = (1920, 1080)) -> List[str]:
        """Resize and prepare images for video composition"""
        prepared_images = []
        
        if not self.images:
            # Create a default black image if no images provided
            default_img_path = os.path.join(self.temp_dir, "default_bg.jpg")
            default_img = Image.new('RGB', target_resolution, color='black')
            default_img.save(default_img_path, quality=95)
            prepared_images.append(default_img_path)
            print("No images provided, created default background")
        else:
            for i, image_path in enumerate(self.images):
                try:
                    # Load and resize image
                    with Image.open(image_path) as img:
                        # Convert to RGB if necessary
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Resize to target resolution maintaining aspect ratio
                        img_resized = self._resize_with_padding(img, target_resolution)
                        
                        # Save prepared image
                        prepared_path = os.path.join(self.temp_dir, f"prepared_{i:03d}.jpg")
                        img_resized.save(prepared_path, quality=95)
                        prepared_images.append(prepared_path)
                        print(f"Prepared image {i+1}: {prepared_path}")
                        
                except Exception as e:
                    print(f"Error preparing image {image_path}: {e}")
                    continue
        
        return prepared_images
    
    def _resize_with_padding(self, img: Image.Image, target_size: tuple) -> Image.Image:
        """Resize image to target size with padding to maintain aspect ratio"""
        target_w, target_h = target_size
        img_w, img_h = img.size
        
        # Calculate scaling factor
        scale = min(target_w / img_w, target_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        
        # Resize image
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Create new image with target size and paste resized image
        result = Image.new('RGB', target_size, color='black')
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        result.paste(img_resized, (paste_x, paste_y))
        
        return result
    
    def create_slideshow_video(
        self, 
        resolution: str = "1920x1080",
        fps: int = 30,
        transition_duration: float = 1.0,
        image_distribution: str = "equal",
        audio_fade_duration: float = 1.0,  # ✅ NEW PARAMETER
        audio_silence_duration: float = 0.5  # ✅ NEW PARAMETER
    ) -> str:
        """Create video using FFmpeg with slideshow of images and combined audio"""
        
        width, height = map(int, resolution.split('x'))
        
        # Step 1: Combine all audio files with enhanced transitions
        combined_audio_path = self._combine_audio_files(audio_fade_duration, audio_silence_duration)
        
        # Step 2: Prepare images
        prepared_images = self._prepare_images((width, height))
        
        if not prepared_images:
            raise Exception("No images available for video creation")
        
        # Step 3: Calculate timing based on combined audio duration
        if image_distribution == "equal":
            image_duration = self.total_duration / len(prepared_images)
        else:
            # For future custom timing implementation
            image_duration = self.total_duration / len(prepared_images)
        
        print(f"Creating multi-audio slideshow: {len(prepared_images)} images, {image_duration:.2f}s each")
        print(f"Total video duration will be: {self.total_duration:.2f}s")
        
        # Step 4: Generate output filename
        output_filename = f"video_multi_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Step 5: Create video using the combined audio
        if len(prepared_images) == 1:
            # Single image case
            success = self._create_single_image_video(
                prepared_images[0], combined_audio_path, output_path, 
                width, height, fps
            )
        else:
            # Multiple images with simple concatenation
            success = self._create_multi_image_video(
                prepared_images, combined_audio_path, output_path,
                width, height, fps, transition_duration, image_duration
            )
        
        if success:
            print(f"Multi-audio video created successfully: {output_path}")
            return output_path
        else:
            raise Exception("Failed to create multi-audio video")
    
    def create_video_with_effects(
        self,
        resolution: str = "1920x1080",
        fps: int = 30,
        add_ken_burns: bool = False,
        image_distribution: str = "equal"
    ) -> str:
        """Create video with additional effects using combined audio"""
        
        if add_ken_burns:
            return self._create_ken_burns_video(resolution, fps, image_distribution)
        else:
            return self.create_slideshow_video(resolution, fps, 1.5, image_distribution)
    
    def _create_single_image_video(self, image_path: str, audio_path: str, output_path: str,
                                  width: int, height: int, fps: int) -> bool:
        """Create video from single image and combined audio"""
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1', '-i', image_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
            '-r', str(fps),
            '-shortest',
            output_path
        ]
        
        return self._execute_ffmpeg_command(cmd)
    
    def _create_multi_image_video(self, images: List[str], audio_path: str, output_path: str,
                                 width: int, height: int, fps: int, 
                                 transition_duration: float, image_duration: float) -> bool:
        """Create video from multiple images with crossfade transitions and combined audio"""
        
        # Create individual video segments first
        segment_paths = []
        
        for i, image_path in enumerate(images):
            segment_path = os.path.join(self.temp_dir, f"segment_{i:03d}.mp4")
            
            # Calculate duration for this segment
            if i == len(images) - 1:
                # Last segment - fill remaining time
                segment_duration = self.total_duration - (i * image_duration)
            else:
                segment_duration = image_duration + transition_duration  # Add overlap for crossfade
            
            # Create segment
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1', '-i', image_path,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                '-r', str(fps),
                '-t', str(segment_duration),
                segment_path
            ]
            
            if self._execute_ffmpeg_command(cmd):
                segment_paths.append(segment_path)
                print(f"Created segment {i+1}: {segment_path} ({segment_duration:.2f}s)")
            else:
                print(f"Failed to create segment {i+1}")
                return False
        
        if not segment_paths:
            return False
        
        # Now create the final video with crossfade transitions and combined audio
        return self._create_crossfade_video(segment_paths, audio_path, output_path, 
                                          transition_duration, image_duration)
    
    def _create_crossfade_video(self, segment_paths: List[str], audio_path: str, 
                            output_path: str, transition_duration: float, 
                            image_duration: float) -> bool:
        """Create final video with crossfade transitions and combined audio"""
        
        if len(segment_paths) == 1:
            # Only one segment, just add combined audio
            cmd = [
                'ffmpeg', '-y',
                '-i', segment_paths[0],
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                output_path
            ]
            return self._execute_ffmpeg_command(cmd)
        
        # For multiple segments, let's use a simpler approach that's more reliable
        # Instead of complex crossfades, let's just concatenate the segments
        print(f"Creating video from {len(segment_paths)} segments with simple concatenation")
        
        # Create a concat file for ffmpeg
        concat_file_path = os.path.join(self.temp_dir, "concat_list.txt")
        with open(concat_file_path, 'w') as f:
            for segment_path in segment_paths:
                f.write(f"file '{os.path.abspath(segment_path)}'\n")
        
        # Use concat demuxer - simpler and more reliable
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-pix_fmt', 'yuv420p',
            '-map', '0:v',  # Use video from concat
            '-map', '1:a',  # Use audio from combined audio file
            '-shortest',
            output_path
        ]
        
        print(f"Using concat demuxer for {len(segment_paths)} segments")
        return self._execute_ffmpeg_command(cmd)
    
    def _create_ken_burns_video(self, resolution: str, fps: int, image_distribution: str) -> str:
        """Create video with Ken Burns (zoom/pan) effect using combined audio - simplified version"""
        width, height = map(int, resolution.split('x'))
        prepared_images = self._prepare_images((int(width * 1.2), int(height * 1.2)))  # Slightly larger for zoom
        
        if not prepared_images:
            raise Exception("No images available for video creation")
        
        # Generate output filename
        output_filename = f"video_multi_kb_{uuid.uuid4().hex[:8]}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # For now, use simple slideshow - Ken Burns is complex and can be added later
        print("Ken Burns effect requested for multi-audio - using enhanced slideshow for now")
        return self.create_slideshow_video(resolution, fps, 1.5, image_distribution)
    
    def _execute_ffmpeg_command(self, cmd: List[str]) -> bool:
        """Execute FFmpeg command with proper error handling"""
        try:
            print(f"Executing: {' '.join(cmd[:8])}...")  # Show first part of command
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg command failed:")
            print(f"Command: {' '.join(cmd)}")
            print(f"Return code: {e.returncode}")
            print(f"STDERR: {e.stderr}")
            print(f"STDOUT: {e.stdout}")
            return False
    
    def cleanup(self):
        """Clean up temporary files"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")

def create_video_from_audio_and_images(
    audio_file_path: str,
    image_paths: List[str],
    output_path: str,
    fps: int = 30,
    resolution: str = "1920x1080",
    transition_duration: float = 1.0,
    transition_type: str = "fade",
    add_ken_burns: bool = False,
    add_audio_visualization: bool = False
) -> str:
    """Enhanced video creation function using FFmpeg"""
    
    print(f"Creating video from {len(image_paths)} images and audio: {audio_file_path}")
    
    composer = FFmpegVideoComposer(audio_file_path, image_paths)
    
    try:
        if add_ken_burns or add_audio_visualization:
            video_path = composer.create_video_with_effects(
                resolution=resolution,
                fps=fps,
                transition_type=transition_type,
                add_ken_burns=add_ken_burns,
                add_audio_visualization=add_audio_visualization
            )
        else:
            video_path = composer.create_slideshow_video(
                resolution=resolution,
                fps=fps,
                transition_duration=transition_duration
            )
        
        # Move to desired output path if different
        if video_path != output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            shutil.move(video_path, output_path)
            video_path = output_path
        
        print(f"Video created successfully: {video_path}")
        return video_path
        
    finally:
        composer.cleanup()