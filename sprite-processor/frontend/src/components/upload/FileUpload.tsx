'use client'

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Image as ImageIcon } from 'lucide-react'

interface FileUploadProps {
    onFileSelect: (file: File) => void
}

export function FileUpload({ onFileSelect }: FileUploadProps) {
    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles[0]) {
            onFileSelect(acceptedFiles[0])
        }
    }, [onFileSelect])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.png', '.jpg', '.jpeg', '.webp']
        },
        multiple: false
    })

    return (
        <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${isDragActive
                    ? 'border-blue-500 bg-blue-50 scale-105'
                    : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                }`}
        >
            <input {...getInputProps()} />

            <div className="flex flex-col items-center space-y-4">
                <div className={`w-16 h-16 rounded-full flex items-center justify-center ${isDragActive ? 'bg-blue-100' : 'bg-gray-100'
                    }`}>
                    {isDragActive ? (
                        <Upload className="w-8 h-8 text-blue-600" />
                    ) : (
                        <ImageIcon className="w-8 h-8 text-gray-600" />
                    )}
                </div>

                <div>
                    <p className="text-lg font-medium text-gray-900">
                        {isDragActive
                            ? 'Drop the image here...'
                            : 'Drag & drop an image here'}
                    </p>
                    <p className="text-sm text-gray-500 mt-1">
                        or click to select a file
                    </p>
                </div>

                <div className="text-xs text-gray-400">
                    Supports PNG, JPG, JPEG, WEBP (max 10MB)
                </div>
            </div>
        </div>
    )
}
