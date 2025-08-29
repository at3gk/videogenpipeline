import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { AudioFile } from '../types';
import { projectsApi } from '../services/api';
import toast from 'react-hot-toast';

interface AudioUploadProps {
  projectId: string;
  onUploadComplete: (file: AudioFile | null) => void;
  maxFileSize?: number;
  acceptedFormats?: string[];
}

export const AudioUpload: React.FC<AudioUploadProps> = ({ 
  projectId, 
  onUploadComplete,
  maxFileSize = 100 * 1024 * 1024, // 100MB
  acceptedFormats = ['.mp3', '.wav', '.m4a', '.flac']
}) => {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [existingFiles, setExistingFiles] = useState<AudioFile[]>([]);
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [playingFileId, setPlayingFileId] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<{ [key: string]: number }>({});
  const [duration, setDuration] = useState<{ [key: string]: number }>({});
  const audioRefs = useRef<{ [key: string]: HTMLAudioElement }>({});

  useEffect(() => {
    loadExistingAudioFiles();
  }, [projectId]);

  const loadExistingAudioFiles = async () => {
    setIsLoading(true);
    try {
      const files = await projectsApi.getAudioFiles(projectId);
      setExistingFiles(files);
      
      // Don't auto-select anymore - let user choose
      if (files.length === 0) {
        setShowUploadForm(true);
      }
    } catch (error) {
      console.error('Failed to load audio files:', error);
      setShowUploadForm(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    setIsUploading(true);
    setUploadProgress(0);
    
    try {
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);
      
      const audioFile = await projectsApi.uploadAudio(projectId, file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      setExistingFiles(prev => [...prev, audioFile]);
      setSelectedFile(audioFile);
      setShowUploadForm(false);
      
      onUploadComplete(audioFile);
      toast.success('Audio file uploaded successfully!');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleSelectFile = (audioFile: AudioFile) => {
    setSelectedFile(audioFile);
    onUploadComplete(audioFile);
    toast.success(`Selected: ${audioFile.filename}`);
  };

  const handleRemoveFile = async (fileId: string) => {
    if (playingFileId === fileId) {
      handleStopAudio(fileId);
    }
    
    try {
      await projectsApi.removeAudioFile(projectId, fileId);
      setExistingFiles(prev => prev.filter(f => f.id !== fileId));
      
      if (selectedFile?.id === fileId) {
        setSelectedFile(null);
        onUploadComplete(null);
      }
      
      toast.success('Audio file removed');
    } catch (error) {
      console.error('Failed to remove file:', error);
      toast.error('Failed to remove file');
    }
  };

  const getAudioUrl = (audioFile: AudioFile) => {
    const baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
    if (audioFile.file_path?.startsWith('/')) {
      return `${baseUrl}${audioFile.file_path}`;
    }
    return `${baseUrl}/uploads/${audioFile.file_path?.split('/').pop() || audioFile.filename}`;
  };

  const handlePlayAudio = (audioFile: AudioFile) => {
    const audioUrl = getAudioUrl(audioFile);
    
    // Stop any currently playing audio
    if (playingFileId && playingFileId !== audioFile.id) {
      handleStopAudio(playingFileId);
    }

    if (playingFileId === audioFile.id) {
      // Pause current
      handlePauseAudio(audioFile.id);
    } else {
      // Play new audio
      if (!audioRefs.current[audioFile.id]) {
        audioRefs.current[audioFile.id] = new Audio(audioUrl);
        
        const audio = audioRefs.current[audioFile.id];
        
        audio.addEventListener('loadedmetadata', () => {
          setDuration(prev => ({ ...prev, [audioFile.id]: audio.duration }));
        });
        
        audio.addEventListener('timeupdate', () => {
          setCurrentTime(prev => ({ ...prev, [audioFile.id]: audio.currentTime }));
        });
        
        audio.addEventListener('ended', () => {
          setPlayingFileId(null);
          setCurrentTime(prev => ({ ...prev, [audioFile.id]: 0 }));
        });
      }
      
      audioRefs.current[audioFile.id].play()
        .then(() => {
          setPlayingFileId(audioFile.id);
        })
        .catch((error) => {
          console.error('Failed to play audio:', error);
          toast.error('Failed to play audio file');
        });
    }
  };

  const handlePauseAudio = (fileId: string) => {
    if (audioRefs.current[fileId]) {
      audioRefs.current[fileId].pause();
      setPlayingFileId(null);
    }
  };

  const handleStopAudio = (fileId: string) => {
    if (audioRefs.current[fileId]) {
      audioRefs.current[fileId].pause();
      audioRefs.current[fileId].currentTime = 0;
      setPlayingFileId(null);
      setCurrentTime(prev => ({ ...prev, [fileId]: 0 }));
    }
  };

  const handleSeekAudio = (fileId: string, seekTime: number) => {
    if (audioRefs.current[fileId]) {
      audioRefs.current[fileId].currentTime = seekTime;
      setCurrentTime(prev => ({ ...prev, [fileId]: seekTime }));
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'audio/mp4': ['.m4a'],
      'audio/flac': ['.flac']
    },
    maxSize: maxFileSize,
    multiple: false,
    onDrop: handleFileUpload
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatTime = (seconds: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Clean up audio references when component unmounts
  useEffect(() => {
    return () => {
      Object.values(audioRefs.current).forEach(audio => {
        audio.pause();
        audio.remove();
      });
    };
  }, []);

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl mx-auto text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-2 text-gray-600">Loading audio files...</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Existing Files Section */}
      {existingFiles.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">
              Choose Audio Track ({existingFiles.length} available)
            </h3>
            <button
              onClick={() => setShowUploadForm(!showUploadForm)}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              {showUploadForm ? 'Cancel Upload' : '+ Upload New'}
            </button>
          </div>

          <div className="space-y-4">
            {existingFiles.map((audioFile) => {
              const isSelected = selectedFile?.id === audioFile.id;
              const isPlaying = playingFileId === audioFile.id;
              const currentTimeForFile = currentTime[audioFile.id] || 0;
              const durationForFile = duration[audioFile.id] || audioFile.duration_seconds || 0;
              
              return (
                <div
                  key={audioFile.id}
                  className={`border rounded-lg p-4 transition-all ${
                    isSelected 
                      ? 'border-blue-500 bg-blue-50 shadow-md' 
                      : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                >
                  {/* File Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => handleSelectFile(audioFile)}
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors ${
                          isSelected 
                            ? 'border-blue-500 bg-blue-500' 
                            : 'border-gray-300 hover:border-blue-400'
                        }`}
                      >
                        {isSelected && (
                          <div className="w-2 h-2 bg-white rounded-full"></div>
                        )}
                      </button>
                      <div>
                        <p className="font-medium text-gray-900 truncate max-w-xs">
                          {audioFile.filename}
                        </p>
                        <p className="text-sm text-gray-500">
                          {audioFile.file_size_bytes && formatFileSize(audioFile.file_size_bytes)}
                          {durationForFile > 0 && ` • ${formatTime(durationForFile)}`}
                          {audioFile.uploaded_at && ` • ${new Date(audioFile.uploaded_at).toLocaleDateString()}`}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveFile(audioFile.id)}
                      className="text-red-600 hover:text-red-800 p-1 opacity-70 hover:opacity-100"
                      title="Remove file"
                    >
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>

                  {/* Audio Player Controls */}
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      {/* Play/Pause Button */}
                      <button
                        onClick={() => handlePlayAudio(audioFile)}
                        className="flex-shrink-0 w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
                      >
                        {isPlaying ? (
                          <svg className="w-5 h-5 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5 text-gray-700 ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1.586a1 1 0 01.707.293l2.414 2.414a1 1 0 00.707.293H15" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 18l13.5-13.5M18 5L4.5 18.5" />
                            <polygon points="5,3 19,12 5,21" fill="currentColor" stroke="none" />
                          </svg>
                        )}
                      </button>

                      {/* Progress Bar */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-1">
                          <span>{formatTime(currentTimeForFile)}</span>
                          <span>/</span>
                          <span>{formatTime(durationForFile)}</span>
                        </div>
                        <div 
                          className="w-full bg-gray-200 rounded-full h-2 cursor-pointer"
                          onClick={(e) => {
                            if (durationForFile > 0) {
                              const rect = e.currentTarget.getBoundingClientRect();
                              const clickX = e.clientX - rect.left;
                              const clickRatio = clickX / rect.width;
                              const seekTime = clickRatio * durationForFile;
                              handleSeekAudio(audioFile.id, seekTime);
                            }
                          }}
                        >
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ 
                              width: durationForFile > 0 ? `${(currentTimeForFile / durationForFile) * 100}%` : '0%' 
                            }}
                          />
                        </div>
                      </div>

                      {/* Stop Button */}
                      {isPlaying && (
                        <button
                          onClick={() => handleStopAudio(audioFile.id)}
                          className="flex-shrink-0 w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
                        >
                          <svg className="w-4 h-4 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <rect x="6" y="6" width="12" height="12" fill="currentColor" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selection Status */}
          {selectedFile ? (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className="font-medium text-green-800">
                    Selected: {selectedFile.filename}
                  </p>
                  <p className="text-sm text-green-600">
                    Ready to proceed to image generation
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>
                  <p className="font-medium text-yellow-800">
                    No audio track selected
                  </p>
                  <p className="text-sm text-yellow-600">
                    Please select an audio file above or upload a new one below to continue
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Upload New File Section */}
      {(showUploadForm || existingFiles.length === 0) && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900">
              {existingFiles.length > 0 ? 'Upload New Audio File' : 'Upload Audio File'}
            </h3>
            {existingFiles.length > 0 && (
              <button
                onClick={() => setShowUploadForm(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
          
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive 
                ? 'border-blue-400 bg-blue-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
          >
            <input {...getInputProps()} />
            {isUploading ? (
              <div className="space-y-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-gray-600">Uploading... {uploadProgress}%</p>
              </div>
            ) : (
              <div className="space-y-4">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <div>
                  <p className="text-xl font-medium text-gray-900">
                    Drop your audio file here
                  </p>
                  <p className="text-gray-500">
                    or click to browse ({acceptedFormats.join(', ')}) - max {formatFileSize(maxFileSize)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};