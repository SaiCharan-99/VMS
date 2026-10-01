import { Maximize, Pause, Play } from "lucide-react";
import { forwardRef, useImperativeHandle, useRef, useState, type KeyboardEvent } from "react";
import { formatDuration } from "@/lib/format";

export interface VideoPlayerHandle {
  seek: (t: number) => void;
}

const SKIP_S = 5;

/** Native <video> with minimal custom controls. Keys (when focused): Space, J/K = ∓5 s. */
export const VideoPlayer = forwardRef<
  VideoPlayerHandle,
  { src: string; label: string; onTime?: (t: number, duration: number) => void }
>(function VideoPlayer({ src, label, onTime }, ref) {
  const video = useRef<HTMLVideoElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(false);

  const seek = (t: number) => {
    const v = video.current;
    if (!v) return;
    const max = Number.isFinite(v.duration) ? v.duration : t;
    v.currentTime = Math.max(0, Math.min(max, t));
  };
  useImperativeHandle(ref, () => ({ seek }), []);

  const toggle = () => {
    const v = video.current;
    if (!v) return;
    if (v.paused) void v.play().catch(() => {});
    else v.pause();
  };

  const onKey = (e: KeyboardEvent) => {
    if ((e.target as HTMLElement).tagName === "INPUT") return;
    const v = video.current;
    if (!v) return;
    if (e.key === " ") {
      e.preventDefault();
      toggle();
    } else if (e.key === "j" || e.key === "J") {
      seek(v.currentTime - SKIP_S);
    } else if (e.key === "k" || e.key === "K") {
      seek(v.currentTime + SKIP_S);
    }
  };

  return (
    // The focusable player region owns the Space / J / K shortcuts.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <div
      ref={box}
      role="group"
      aria-label={`Video player: ${label}. Space plays or pauses, J and K skip 5 seconds.`}
      // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex
      tabIndex={0}
      onKeyDown={onKey}
      className="relative aspect-video overflow-hidden rounded-card bg-[#1d1f24]"
    >
      {/* Warehouse recordings have no speech, so there are no captions to show. */}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        ref={video}
        src={src}
        preload="metadata"
        playsInline
        className="h-full w-full object-contain"
        onClick={toggle}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onError={() => setError(true)}
        onLoadedMetadata={(e) => {
          setDuration(e.currentTarget.duration);
          onTime?.(e.currentTarget.currentTime, e.currentTarget.duration);
        }}
        onTimeUpdate={(e) => {
          setTime(e.currentTarget.currentTime);
          onTime?.(e.currentTarget.currentTime, e.currentTarget.duration);
        }}
      />
      {error && (
        <div className="absolute inset-0 grid place-items-center px-4 text-center text-sm text-white/80">
          The video couldn&apos;t be loaded. Reload the page to try again.
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 flex items-center gap-2.5 bg-gradient-to-t from-black/60 to-transparent px-3 pb-3 pt-6 text-xs text-white">
        <button
          type="button"
          onClick={toggle}
          aria-label={playing ? "Pause" : "Play"}
          className="grid h-[30px] w-[30px] flex-none place-items-center rounded-full bg-white/20 hover:bg-white/30 focus-visible:outline-white"
        >
          {playing ? <Pause size={14} aria-hidden /> : <Play size={14} aria-hidden />}
        </button>
        <span className="font-mono tabular-nums">
          {formatDuration(time)} / {formatDuration(duration)}
        </span>
        <input
          type="range"
          aria-label="Seek"
          min={0}
          max={duration || 0}
          step={0.1}
          value={time}
          onChange={(e) => seek(Number(e.target.value))}
          className="min-w-0 flex-1 accent-white"
        />
        <button
          type="button"
          aria-label="Full screen"
          onClick={() => void box.current?.requestFullscreen?.().catch(() => {})}
          className="grid h-[30px] w-[30px] flex-none place-items-center rounded-full hover:bg-white/20 focus-visible:outline-white"
        >
          <Maximize size={14} aria-hidden />
        </button>
      </div>
    </div>
  );
});
