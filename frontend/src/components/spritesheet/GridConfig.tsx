'use client'

import { Grid, Hash } from 'lucide-react'

interface GridConfigProps {
    config: { rows: number; cols: number }
    onChange: (config: { rows: number; cols: number }) => void
    frames: number
    onFramesChange: (frames: number) => void
    /** Total frames available in source (e.g. GIF frame count). */
    sourceFrameCount?: number
    gifMode?: boolean
}

function autoGrid(frameCount: number): { cols: number; rows: number } {
    const cols = Math.ceil(Math.sqrt(frameCount))
    const rows = Math.ceil(frameCount / cols)
    return { cols, rows }
}

export function GridConfig({
    config,
    onChange,
    frames,
    onFramesChange,
    sourceFrameCount,
    gifMode = false,
}: GridConfigProps) {
    const totalGridCells = config.rows * config.cols
    const maxSelectable = sourceFrameCount ?? totalGridCells

    const applyFrameCount = (count: number) => {
        const clamped = Math.min(Math.max(1, count), maxSelectable)
        onFramesChange(clamped)
        if (gifMode) {
            onChange(autoGrid(clamped))
        }
    }

    return (
        <div className="bg-white rounded-lg border p-6 space-y-6">
            <div className="flex items-center gap-2 mb-4">
                <Grid className="w-5 h-5 text-gray-600" />
                <h3 className="text-lg font-semibold text-gray-900">Grid Configuration</h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Columns
                    </label>
                    <input
                        type="number"
                        min="1"
                        max="30"
                        value={config.cols}
                        onChange={(e) => onChange({ ...config, cols: parseInt(e.target.value) || 1 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Rows
                    </label>
                    <input
                        type="number"
                        min="1"
                        max="30"
                        value={config.rows}
                        onChange={(e) => onChange({ ...config, rows: parseInt(e.target.value) || 1 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                    <Hash className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-700">
                        {gifMode ? 'Output Grid' : 'Total Grid Cells'}
                    </span>
                </div>
                <div className="text-2xl font-bold text-gray-900">{totalGridCells}</div>
                {gifMode && sourceFrameCount && (
                    <p className="text-xs text-gray-500 mt-1">
                        Source GIF has {sourceFrameCount} frames
                    </p>
                )}
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Frames to Extract
                </label>
                <input
                    type="number"
                    min="1"
                    max={maxSelectable}
                    value={frames}
                    onChange={(e) => applyFrameCount(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                    {gifMode
                        ? `Sample ${frames} frames evenly across the GIF (max ${maxSelectable})`
                        : `Process the first ${frames} frames from the grid`}
                </p>
            </div>

            {gifMode && (
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Frame Presets
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                        {[12, 24, 48].map((preset) => (
                            <button
                                key={preset}
                                type="button"
                                onClick={() => applyFrameCount(Math.min(preset, maxSelectable))}
                                className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                            >
                                {Math.min(preset, maxSelectable)}
                            </button>
                        ))}
                        <button
                            type="button"
                            onClick={() => applyFrameCount(maxSelectable)}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                        >
                            All
                        </button>
                    </div>
                </div>
            )}

            {!gifMode && (
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Quick Presets
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                        <button
                            type="button"
                            onClick={() => onChange({ rows: 2, cols: 5 })}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                        >
                            5×2 (10 frames)
                        </button>
                        <button
                            type="button"
                            onClick={() => onChange({ rows: 3, cols: 4 })}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                        >
                            4×3 (12 frames)
                        </button>
                        <button
                            type="button"
                            onClick={() => onChange({ rows: 4, cols: 4 })}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                        >
                            4×4 (16 frames)
                        </button>
                        <button
                            type="button"
                            onClick={() => onChange({ rows: 5, cols: 5 })}
                            className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                        >
                            5×5 (25 frames)
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
