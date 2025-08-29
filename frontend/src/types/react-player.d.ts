declare module 'react-player' {
  import React from 'react';

  interface ReactPlayerProps {
    url?: string | string[];
    playing?: boolean;
    loop?: boolean;
    controls?: boolean;
    volume?: number;
    muted?: boolean;
    playbackRate?: number;
    width?: string | number;
    height?: string | number;
    style?: React.CSSProperties;
    progressInterval?: number;
    playsinline?: boolean;
    pip?: boolean;
    stopOnUnmount?: boolean;
    light?: boolean | string;
    wrapper?: React.ComponentType<any>;
    config?: any;
    onReady?: () => void;
    onStart?: () => void;
    onPlay?: () => void;
    onPause?: () => void;
    onBuffer?: () => void;
    onBufferEnd?: () => void;
    onEnded?: () => void;
    onError?: (error: any) => void;
    onProgress?: (state: { played: number; playedSeconds: number; loaded: number; loadedSeconds: number }) => void;
    onDuration?: (duration: number) => void;
    onSeek?: (seconds: number) => void;
    onEnablePIP?: () => void;
    onDisablePIP?: () => void;
    [key: string]: any;
  }

  const ReactPlayer: React.ForwardRefExoticComponent<ReactPlayerProps & React.RefAttributes<any>>;
  export default ReactPlayer;
}
