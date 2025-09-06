'use client'

import { useState, useEffect } from 'react'
import { Eye, Grid } from 'lucide-react'

interface SpritesheetViewerProps {
    file: File
    gridConfig: { rows: number; cols: number }
    frames: number
}

export function SpritesheetViewer({ file, gridConfig, frames }: SpritesheetViewerProps) {
    const [preview, setPreview] = useState<string | null>(null)

    useEffect(() => {
        const reader = new FileReader()
        reader.onload = (e) => {
            setPreview(e.target?.result as string)
        }
        reader.readAsDataURL(file)
    }, [file])

    if (!preview) return null

    return (
        <div className="bg-white rounded-lg border p-6">
            <div className="flex items-center gap-2 mb-4">
                <Eye className="w-5 h-5 text-gray-600" />
                <h3 className="text-lg font-semibold text-gray-900">Spritesheet Preview</h3>
            </div>

            <div className="space-y-4">
                <div className="bg-gray-100 rounded-lg p-4 overflow-auto max-h-96">
                    <img
                        src={preview}
                        alt="Spritesheet preview"
                        className="max-w-full h-auto"
                    />
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="font-medium text-gray-700">File:</span>
                        <p className="text-gray-600 truncate">{file.name}</p>
                    </div>
                    <div>
                        <span className="font-medium text-gray-700">Size:</span>
                        <p className="text-gray-600">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                    <div>
                        <span className="font-medium text-gray-700">Grid:</span>
                        <p className="text-gray-600">{gridConfig.cols}×{gridConfig.rows}</p>
                    </div>
                    <div>
                        <span className="font-medium text-gray-700">Frames:</span>
                        <p className="text-gray-600">{frames} of {gridConfig.rows * gridConfig.cols}</p>
                    </div>
                </div>

                {/* Grid Overlay Visualization */}
                <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                        <Grid className="w-4 h-4 text-gray-600" />
                        <span className="text-sm font-medium text-gray-700">Grid Layout</span>
                    </div>

                    <div
                        className="grid gap-1 mx-auto"
                        style={{
                            gridTemplateColumns: `repeat(${gridConfig.cols}, 1fr)`,
                            gridTemplateRows: `repeat(${gridConfig.rows}, 1fr)`,
                            maxWidth: '200px'
                        }}
                    >
                        {Array.from({ length: gridConfig.rows * gridConfig.cols }, (_, i) => (
                            <div
                                key={i}
                                className={`aspect-square rounded border-2 flex items-center justify-center text-xs font-medium ${i < frames
                                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                                        : 'bg-gray-100 border-gray-300 text-gray-500'
                                    }`}
                            >
                                {i + 1}
                            </div>
                        ))}
                    </div>

                    <p className="text-xs text-gray-500 mt-2 text-center">
                        Blue cells will be processed ({frames} frames)
                    </p>
                </div>
            </div>
        </div>
    )
}
