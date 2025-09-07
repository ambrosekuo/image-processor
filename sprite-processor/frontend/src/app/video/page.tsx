'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Video, Download, Settings, Play, Pause, RotateCcw } from 'lucide-react'
import { apiClient, VideoToGifConfig, VideoAnalysisResponse } from '../../lib/api'

export default function VideoPage() {
    const [uploadedFile, setUploadedFile] = useState<File | null>(null)
    const [isProcessing, setIsProcessing] = useState(false)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [gifBlob, setGifBlob] = useState<Blob | null>(null)
    const [gifUrl, setGifUrl] = useState<string | null>(null)
    const [analysis, setAnalysis] = useState<VideoAnalysisResponse | null>(null)
    const [error, setError] = useState<string | null>(null)
    const [isConvertingToSpritesheet, setIsConvertingToSpritesheet] = useState(false)
    const [spritesheetBlob, setSpritesheetBlob] = useState<Blob | null>(null)
    const [spritesheetUrl, setSpritesheetUrl] = useState<string | null>(null)
    const [spritesheetConfig, setSpritesheetConfig] = useState({
        grid: '5x2',
        frames: 10
    })
    const [config, setConfig] = useState<VideoToGifConfig>({
        fps: 10,
        duration: undefined,
        maxWidth: 480,
        maxHeight: 480
    })

    const onDrop = useCallback((acceptedFiles: File[]) => {
        const file = acceptedFiles[0]
        if (file) {
            setUploadedFile(file)
            setGifBlob(null)
            setGifUrl(null)
            setAnalysis(null)
            setError(null)
        }
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm']
        },
        multiple: false
    })

    const analyzeVideo = async () => {
        if (!uploadedFile) return

        setIsAnalyzing(true)
        setError(null)

        try {
            const result = await apiClient.analyzeVideo(uploadedFile)
            setAnalysis(result)

            // Auto-update config with recommendations
            setConfig(prev => ({
                ...prev,
                fps: result.analysis.recommended_fps,
                duration: result.analysis.recommended_duration,
                maxWidth: Math.min(480, result.analysis.size[0]),
                maxHeight: Math.min(480, result.analysis.size[1])
            }))
        } catch (err) {
            setError(`Analysis failed: ${err}`)
        } finally {
            setIsAnalyzing(false)
        }
    }

    const processVideo = async () => {
        if (!uploadedFile) return

        setIsProcessing(true)
        setError(null)

        try {
            const blob = await apiClient.videoToGif(uploadedFile, config)
            setGifBlob(blob)

            // Create URL for display
            const url = URL.createObjectURL(blob)
            setGifUrl(url)
        } catch (err) {
            setError(`Processing failed: ${err}`)
        } finally {
            setIsProcessing(false)
        }
    }

    const downloadGif = () => {
        if (!gifBlob) return

        const url = URL.createObjectURL(gifBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}.gif`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const convertGifToSpritesheet = async () => {
        if (!gifBlob) return

        setIsConvertingToSpritesheet(true)
        setError(null)

        try {
            // Create a File object from the GIF blob
            const gifFile = new File([gifBlob], 'converted.gif', { type: 'image/gif' })

            const response = await apiClient.processSpritesheet(gifFile, {
                grid: spritesheetConfig.grid,
                frames: spritesheetConfig.frames
            })

            if (response.success && response.downloadUrl) {
                // The API client already provides the download URL
                setSpritesheetUrl(response.downloadUrl)
                
                // Fetch the blob for download functionality
                const blobResponse = await fetch(response.downloadUrl)
                const blob = await blobResponse.blob()
                setSpritesheetBlob(blob)
            } else {
                throw new Error(response.message || 'Spritesheet conversion failed')
            }
        } catch (err) {
            setError(`Spritesheet conversion failed: ${err}`)
        } finally {
            setIsConvertingToSpritesheet(false)
        }
    }

    const downloadSpritesheet = () => {
        if (!spritesheetBlob) return

        const url = URL.createObjectURL(spritesheetBlob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}_spritesheet.png`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const reset = () => {
        setUploadedFile(null)
        setGifBlob(null)
        setGifUrl(null)
        setAnalysis(null)
        setError(null)
        setSpritesheetBlob(null)
        setSpritesheetUrl(null)
        setConfig({
            fps: 10,
            duration: undefined,
            maxWidth: 480,
            maxHeight: 480
        })
        setSpritesheetConfig({
            grid: '5x2',
            frames: 10
        })
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-6xl mx-auto px-4 py-8">
                {/* Header */}
                <div className="text-center mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        Video to GIF Converter
                    </h1>
                    <p className="text-lg text-gray-600">
                        Upload a video and convert it to an optimized GIF with custom settings
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Upload Section */}
                    <div className="space-y-6">
                        {/* File Upload */}
                        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                <Upload className="w-5 h-5 mr-2" />
                                Upload Video
                            </h2>

                            <div
                                {...getRootProps()}
                                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${isDragActive
                                    ? 'border-blue-400 bg-blue-50'
                                    : 'border-gray-300 hover:border-gray-400'
                                    }`}
                            >
                                <input {...getInputProps()} />
                                <Video className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                                {isDragActive ? (
                                    <p className="text-blue-600">Drop the video file here...</p>
                                ) : (
                                    <div>
                                        <p className="text-gray-600 mb-2">
                                            Drag & drop a video file here, or click to select
                                        </p>
                                        <p className="text-sm text-gray-500">
                                            Supports MP4, MOV, AVI, MKV, WebM
                                        </p>
                                    </div>
                                )}
                            </div>

                            {uploadedFile && (
                                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="font-medium text-gray-900">{uploadedFile.name}</p>
                                            <p className="text-sm text-gray-500">
                                                {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                                            </p>
                                        </div>
                                        <button
                                            onClick={reset}
                                            className="text-gray-400 hover:text-gray-600"
                                        >
                                            <RotateCcw className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Analysis Section */}
                        {uploadedFile && !analysis && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Settings className="w-5 h-5 mr-2" />
                                    Video Analysis
                                </h2>
                                <p className="text-gray-600 mb-4">
                                    Analyze your video to get recommended settings for optimal GIF conversion.
                                </p>
                                <button
                                    onClick={analyzeVideo}
                                    disabled={isAnalyzing}
                                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    {isAnalyzing ? 'Analyzing...' : 'Analyze Video'}
                                </button>
                            </div>
                        )}

                        {/* Analysis Results */}
                        {analysis && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                                    Video Analysis Results
                                </h2>
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <span className="text-gray-500">Duration:</span>
                                        <span className="ml-2 font-medium">{analysis.analysis.duration.toFixed(1)}s</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">FPS:</span>
                                        <span className="ml-2 font-medium">{analysis.analysis.fps.toFixed(1)}</span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">Size:</span>
                                        <span className="ml-2 font-medium">
                                            {analysis.analysis.size[0]}×{analysis.analysis.size[1]}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-gray-500">File Size:</span>
                                        <span className="ml-2 font-medium">
                                            {(analysis.analysis.file_size / 1024 / 1024).toFixed(1)} MB
                                        </span>
                                    </div>
                                </div>
                                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                                    <p className="text-sm text-blue-800">
                                        <strong>Recommended:</strong> {analysis.analysis.recommended_fps} FPS,
                                        {analysis.analysis.recommended_duration.toFixed(1)}s duration,
                                        {analysis.analysis.recommended_frames} frames
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Settings */}
                        {uploadedFile && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Settings className="w-5 h-5 mr-2" />
                                    GIF Settings
                                </h2>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Frames Per Second
                                        </label>
                                        <input
                                            type="number"
                                            min="1"
                                            max="30"
                                            value={config.fps}
                                            onChange={(e) => setConfig(prev => ({ ...prev, fps: parseInt(e.target.value) || 10 }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Duration (seconds) - Leave empty for full video
                                        </label>
                                        <input
                                            type="number"
                                            min="0.1"
                                            step="0.1"
                                            value={config.duration || ''}
                                            onChange={(e) => setConfig(prev => ({
                                                ...prev,
                                                duration: e.target.value ? parseFloat(e.target.value) : undefined
                                            }))}
                                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="Full video"
                                        />
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Max Width
                                            </label>
                                            <input
                                                type="number"
                                                min="100"
                                                max="1920"
                                                value={config.maxWidth}
                                                onChange={(e) => setConfig(prev => ({ ...prev, maxWidth: parseInt(e.target.value) || 480 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Max Height
                                            </label>
                                            <input
                                                type="number"
                                                min="100"
                                                max="1080"
                                                value={config.maxHeight}
                                                onChange={(e) => setConfig(prev => ({ ...prev, maxHeight: parseInt(e.target.value) || 480 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    </div>
                                </div>

                                <button
                                    onClick={processVideo}
                                    disabled={isProcessing}
                                    className="w-full mt-6 bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                >
                                    {isProcessing ? 'Processing...' : 'Convert to GIF'}
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Results Section */}
                    <div className="space-y-6">
                        {/* GIF Preview */}
                        {gifUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                                        <Play className="w-5 h-5 mr-2" />
                                        GIF Preview
                                    </h2>
                                    <button
                                        onClick={downloadGif}
                                        className="flex items-center px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-4 h-4 mr-1" />
                                        Download
                                    </button>
                                </div>

                                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                                    <img
                                        src={gifUrl}
                                        alt="Generated GIF"
                                        className="w-full h-full object-contain"
                                    />
                                </div>

                                {gifBlob && (
                                    <div className="mt-4 text-sm text-gray-600">
                                        <p>File size: {(gifBlob.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p>Dimensions: {config.maxWidth}×{config.maxHeight}</p>
                                        <p>FPS: {config.fps}</p>
                                        {config.duration && <p>Duration: {config.duration}s</p>}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* GIF to Spritesheet Conversion */}
                        {gifUrl && !spritesheetUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Settings className="w-5 h-5 mr-2" />
                                    Convert GIF to Spritesheet
                                </h2>

                                <div className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Grid Layout (cols × rows)
                                            </label>
                                            <input
                                                type="text"
                                                value={spritesheetConfig.grid}
                                                onChange={(e) => setSpritesheetConfig(prev => ({ ...prev, grid: e.target.value }))}
                                                placeholder="5x2"
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Number of Frames
                                            </label>
                                            <input
                                                type="number"
                                                min="1"
                                                max="50"
                                                value={spritesheetConfig.frames}
                                                onChange={(e) => setSpritesheetConfig(prev => ({ ...prev, frames: parseInt(e.target.value) || 10 }))}
                                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            />
                                        </div>
                                    </div>

                                    <button
                                        onClick={convertGifToSpritesheet}
                                        disabled={isConvertingToSpritesheet}
                                        className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-purple-400 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                                    >
                                        {isConvertingToSpritesheet ? 'Converting to Spritesheet...' : 'Convert to Spritesheet'}
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* Spritesheet Preview */}
                        {spritesheetUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                                        <Play className="w-5 h-5 mr-2" />
                                        Spritesheet Preview
                                    </h2>
                                    <button
                                        onClick={downloadSpritesheet}
                                        className="flex items-center px-3 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition-colors"
                                    >
                                        <Download className="w-4 h-4 mr-1" />
                                        Download
                                    </button>
                                </div>

                                <div className="aspect-video bg-gray-100 rounded-lg overflow-hidden">
                                    <img
                                        src={spritesheetUrl}
                                        alt="Generated Spritesheet"
                                        className="w-full h-full object-contain"
                                    />
                                </div>

                                {spritesheetBlob && (
                                    <div className="mt-4 text-sm text-gray-600">
                                        <p>File size: {(spritesheetBlob.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p>Grid: {spritesheetConfig.grid}</p>
                                        <p>Frames: {spritesheetConfig.frames}</p>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Error Display */}
                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <p className="text-red-800">{error}</p>
                            </div>
                        )}

                        {/* Instructions */}
                        {!uploadedFile && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                                    How to Use
                                </h2>
                                <ol className="space-y-2 text-gray-600">
                                    <li>1. Upload a video file (MP4, MOV, AVI, etc.)</li>
                                    <li>2. Click "Analyze Video" to get recommended settings</li>
                                    <li>3. Adjust the GIF settings as needed</li>
                                    <li>4. Click "Convert to GIF" to process</li>
                                    <li>5. Preview and download your GIF</li>
                                    <li>6. <strong>NEW:</strong> Convert GIF to spritesheet for game development!</li>
                                </ol>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}