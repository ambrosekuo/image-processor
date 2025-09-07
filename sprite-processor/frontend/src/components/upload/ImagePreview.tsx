'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'

interface ImagePreviewProps {
    file: File
    onRemove?: () => void
}

export function ImagePreview({ file, onRemove }: ImagePreviewProps) {
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
        <div className="relative bg-white rounded-lg border p-4">
            <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-gray-900">Preview</h3>
                {onRemove && (
                    <button
                        onClick={onRemove}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                )}
            </div>

            <div className="space-y-2">
                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                    <img
                        src={preview}
                        alt="Preview"
                        className="w-full h-full object-contain"
                    />
                </div>

                <div className="text-sm text-gray-600">
                    <p><strong>File:</strong> {file.name}</p>
                    <p><strong>Size:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    <p><strong>Type:</strong> {file.type}</p>
                </div>
            </div>
        </div>
    )
}
