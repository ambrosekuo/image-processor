'use client'

import { Grid, Hash } from 'lucide-react'

interface GridConfigProps {
    config: { rows: number; cols: number }
    onChange: (config: { rows: number; cols: number }) => void
    frames: number
    onFramesChange: (frames: number) => void
}

export function GridConfig({ config, onChange, frames, onFramesChange }: GridConfigProps) {
    const totalFrames = config.rows * config.cols

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
                        max="20"
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
                        max="20"
                        value={config.rows}
                        onChange={(e) => onChange({ ...config, rows: parseInt(e.target.value) || 1 })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                    <Hash className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-700">Total Grid Cells</span>
                </div>
                <div className="text-2xl font-bold text-gray-900">{totalFrames}</div>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Frames to Process
                </label>
                <input
                    type="number"
                    min="1"
                    max={totalFrames}
                    value={frames}
                    onChange={(e) => onFramesChange(Math.min(parseInt(e.target.value) || 1, totalFrames))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                    Process only the first {frames} frames from the grid
                </p>
            </div>

            {/* Quick Presets */}
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                    Quick Presets
                </label>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        onClick={() => onChange({ rows: 2, cols: 5 })}
                        className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        5×2 (10 frames)
                    </button>
                    <button
                        onClick={() => onChange({ rows: 3, cols: 4 })}
                        className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        4×3 (12 frames)
                    </button>
                    <button
                        onClick={() => onChange({ rows: 4, cols: 4 })}
                        className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        4×4 (16 frames)
                    </button>
                    <button
                        onClick={() => onChange({ rows: 5, cols: 5 })}
                        className="px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
                    >
                        5×5 (25 frames)
                    </button>
                </div>
            </div>
        </div>
    )
}
