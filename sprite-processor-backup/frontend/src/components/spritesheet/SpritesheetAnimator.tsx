'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import { Play, Pause, RotateCcw, Settings, Download } from 'lucide-react';

interface SpritesheetAnimatorProps {
    spritesheetUrl: string; // URL of the original spritesheet
    gridConfig: { rows: number; cols: number };
    frames: number;
    frameRate?: number;
    loop?: boolean;
    className?: string;
}

type RafId = number | null;

export default function SpritesheetAnimator({
    spritesheetUrl,
    gridConfig,
    frames,
    frameRate = 10,
    loop = true,
    className = '',
}: SpritesheetAnimatorProps) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [customFrameRate, setCustomFrameRate] = useState(frameRate);
    const [showSettings, setShowSettings] = useState(false);
    const [frameUrls, setFrameUrls] = useState<string[]>([]);
    const [loopLocal, setLoopLocal] = useState(loop);

    const rafRef = useRef<RafId>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const objectUrlsRef = useRef<string[]>([]); // for cleanup

    // Sync prop updates
    useEffect(() => setCustomFrameRate(frameRate), [frameRate]);
    useEffect(() => setLoopLocal(loop), [loop]);

    const maxFrames = useMemo(
        () => Math.min(Math.max(frames ?? 0, 0), (gridConfig?.rows ?? 0) * (gridConfig?.cols ?? 0)),
        [frames, gridConfig?.rows, gridConfig?.cols]
    );

    // Extract frames from spritesheet -> object URLs
    useEffect(() => {
        let cancelled = false;

        async function extractFrames() {
            // Cleanup any previous object URLs
            objectUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
            objectUrlsRef.current = [];
            setFrameUrls([]);
            setCurrentFrame(0);

            if (!spritesheetUrl || !gridConfig?.rows || !gridConfig?.cols || !maxFrames) return;

            const img = new Image();
            img.crossOrigin = 'anonymous';

            const loadPromise = new Promise<void>((resolve, reject) => {
                img.onload = () => resolve();
                img.onerror = () => reject(new Error('Failed to load spritesheet image'));
            });

            img.src = spritesheetUrl;
            try {
                await loadPromise;
                // decode for better rendering consistency
                // @ts-ignore - not all TS lib targets include decode
                if (img.decode) await img.decode();
            } catch (e) {
                if (!cancelled) {
                    console.error(e);
                    setFrameUrls([]);
                }
                return;
            }
            if (cancelled) return;

            const canvas = canvasRef.current ?? document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            const frameWidth = img.width / gridConfig.cols;
            const frameHeight = img.height / gridConfig.rows;
            canvas.width = Math.floor(frameWidth);
            canvas.height = Math.floor(frameHeight);

            const urls: string[] = [];
            for (let i = 0; i < maxFrames; i++) {
                const row = Math.floor(i / gridConfig.cols);
                const col = i % gridConfig.cols;
                const sx = Math.floor(col * frameWidth);
                const sy = Math.floor(row * frameHeight);

                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, sx, sy, Math.floor(frameWidth), Math.floor(frameHeight), 0, 0, canvas.width, canvas.height);

                const blob: Blob | null = await new Promise((res) => canvas.toBlob((b) => res(b), 'image/png'));
                if (!blob) continue;
                const objectUrl = URL.createObjectURL(blob);
                objectUrlsRef.current.push(objectUrl);
                urls.push(objectUrl);
            }
            if (!cancelled) setFrameUrls(urls);
        }

        extractFrames();

        return () => {
            cancelled = true;
            // Stop animation if running
            if (rafRef.current != null) {
                cancelAnimationFrame(rafRef.current);
                rafRef.current = null;
            }
            // Revoke any created URLs
            objectUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
            objectUrlsRef.current = [];
        };
    }, [spritesheetUrl, gridConfig?.rows, gridConfig?.cols, maxFrames]);

    // rAF-based animation at custom FPS
    useEffect(() => {
        if (!isPlaying || frameUrls.length === 0) return;

        let last = performance.now();
        let acc = 0;
        const frameDuration = 1000 / Math.max(customFrameRate, 1);

        const tick = (now: number) => {
            acc += now - last;
            last = now;

            while (acc >= frameDuration) {
                acc -= frameDuration;
                setCurrentFrame((prev) => {
                    const next = prev + 1;
                    if (next >= frameUrls.length) {
                        return loopLocal ? 0 : frameUrls.length - 1;
                    }
                    return next;
                });
            }
            rafRef.current = requestAnimationFrame(tick);
        };

        rafRef.current = requestAnimationFrame(tick);
        return () => {
            if (rafRef.current != null) {
                cancelAnimationFrame(rafRef.current);
                rafRef.current = null;
            }
        };
    }, [isPlaying, frameUrls.length, customFrameRate, loopLocal, frameUrls]);

    const togglePlayPause = () => setIsPlaying((p) => !p);

    const resetAnimation = () => {
        setIsPlaying(false);
        setCurrentFrame(0);
    };

    const goToFrame = (frameIndex: number) => {
        setCurrentFrame(frameIndex);
        setIsPlaying(false);
    };

    const downloadFrame = (frameIndex: number) => {
        const url = frameUrls[frameIndex];
        if (url) {
            const link = document.createElement('a');
            link.href = url;
            link.download = `frame_${String(frameIndex).padStart(3, '0')}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    const downloadAllFrames = () => {
        frameUrls.forEach((url, index) => {
            setTimeout(() => {
                const link = document.createElement('a');
                link.href = url;
                link.download = `frame_${String(index).padStart(3, '0')}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }, index * 80);
        });
    };

    if (!spritesheetUrl || frameUrls.length === 0) {
        return (
            <div className={`bg-gray-100 rounded-lg p-8 text-center ${className}`}>
                <p className="text-gray-500">No spritesheet available for animation</p>
                <canvas ref={canvasRef} style={{ display: 'none' }} />
            </div>
        );
    }

    return (
        <div className={`bg-white rounded-lg border p-6 ${className}`}>
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Animation Preview</h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowSettings((s) => !s)}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Animation Settings"
                    >
                        <Settings className="w-4 h-4" />
                    </button>
                    <button
                        onClick={downloadAllFrames}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Download All Frames"
                    >
                        <Download className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Animation Display */}
            <div className="bg-gray-100 rounded-lg p-4 mb-4 flex items-center justify-center min-h-[200px]">
                {frameUrls[currentFrame] && (
                    <img
                        src={frameUrls[currentFrame]}
                        alt={`Frame ${currentFrame + 1}`}
                        className="max-w-full max-h-64 object-contain"
                    />
                )}
            </div>

            {/* Controls */}
            <div className="space-y-4">
                {/* Playback Controls */}
                <div className="flex items-center justify-center gap-3">
                    <button
                        onClick={resetAnimation}
                        className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Reset Animation"
                    >
                        <RotateCcw className="w-4 h-4" />
                    </button>
                    <button
                        onClick={togglePlayPause}
                        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                    >
                        {isPlaying ? (
                            <>
                                <Pause className="w-4 h-4" />
                                Pause
                            </>
                        ) : (
                            <>
                                <Play className="w-4 h-4" />
                                Play
                            </>
                        )}
                    </button>
                </div>

                {/* Frame Navigation */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm text-gray-600">
                        <span>
                            Frame {currentFrame + 1} of {frameUrls.length}
                        </span>
                        <span>{customFrameRate} FPS</span>
                    </div>
                    <div className="flex gap-1 flex-wrap">
                        {frameUrls.map((_, index) => (
                            <button
                                key={index}
                                onClick={() => goToFrame(index)}
                                className={`w-8 h-8 rounded text-xs font-medium transition-colors ${index === currentFrame ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                    }`}
                            >
                                {index + 1}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Settings Panel */}
                {showSettings && (
                    <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Frame Rate (FPS)</label>
                            <input
                                type="range"
                                min={1}
                                max={30}
                                value={customFrameRate}
                                onChange={(e) => setCustomFrameRate(Number(e.target.value))}
                                className="w-full"
                            />
                            <div className="flex justify-between text-xs text-gray-500 mt-1">
                                <span>1 FPS</span>
                                <span>30 FPS</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <input
                                type="checkbox"
                                id="loop"
                                checked={loopLocal}
                                onChange={(e) => setLoopLocal(e.target.checked)}
                                className="rounded"
                            />
                            <label htmlFor="loop" className="text-sm text-gray-700">
                                Loop animation
                            </label>
                        </div>
                    </div>
                )}

                {/* Frame Actions */}
                <div className="flex items-center justify-between pt-2 border-t">
                    <div className="text-sm text-gray-600">Click frame numbers to navigate</div>
                    <button onClick={() => downloadFrame(currentFrame)} className="text-sm text-blue-600 hover:text-blue-800 font-medium">
                        Download Current Frame
                    </button>
                </div>
            </div>

            {/* Hidden canvas for frame extraction */}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
    );
}
