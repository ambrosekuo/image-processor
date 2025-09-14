'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Video, Download, Settings, Play, Pause, RotateCcw, Palette, Grid3x3 } from 'lucide-react'
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

    // New frame processing states
    const [extractedFrames, setExtractedFrames] = useState<any[]>([])
    const [isExtractingFrames, setIsExtractingFrames] = useState(false)
    const [selectedModel, setSelectedModel] = useState('isnet-general-use')
    const [isProcessingFrames, setIsProcessingFrames] = useState(false)
    const [processedFrames, setProcessedFrames] = useState<any[]>([])
    const [isReconstructing, setIsReconstructing] = useState(false)
    const [reconstructedSpritesheet, setReconstructedSpritesheet] = useState<Blob | null>(null)
    const [reconstructedUrl, setReconstructedUrl] = useState<string | null>(null)

    // Per-frame model selection
    const [frameModels, setFrameModels] = useState<{ [key: number]: string }>({})
    const [processingMode, setProcessingMode] = useState<'all' | 'individual'>('individual')
    const [selectedFrameIndex, setSelectedFrameIndex] = useState<number | null>(null)
    const [frameProcessingStatus, setFrameProcessingStatus] = useState<{ [key: number]: 'pending' | 'processing' | 'completed' | 'error' }>({})
    const [individualProcessedFrames, setIndividualProcessedFrames] = useState<{ [key: number]: any }>({})
    const [selectedFrames, setSelectedFrames] = useState<{ [key: number]: boolean }>({})
    const [showProcessed, setShowProcessed] = useState<{ [key: number]: boolean }>({})

    const availableModels = [
        { id: 'isnet-general-use', name: 'ISNet General Use (Recommended)' },
        { id: 'u2net_human_seg', name: 'U2Net Human Segmentation' },
        { id: 'u2net', name: 'U2Net' },
        { id: 'u2netp', name: 'U2NetP (Lightweight)' },
        { id: 'u2net_cloth_seg', name: 'U2Net Cloth Segmentation' },
        { id: 'silueta', name: 'Silueta' }
    ]

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
        setExtractedFrames([])
        setProcessedFrames([])
        setReconstructedSpritesheet(null)
        setReconstructedUrl(null)
        setFrameModels({})
        setProcessingMode('individual')
        setSelectedFrameIndex(null)
        setFrameProcessingStatus({})
        setIndividualProcessedFrames({})
        setSelectedFrames({})
        setShowProcessed({})
    }

    // New frame processing functions
    const extractGifFrames = async () => {
        if (!gifBlob) return

        setIsExtractingFrames(true)
        setError(null)

        try {
            const formData = new FormData()
            formData.append('file', gifBlob, 'converted.gif')
            formData.append('grid', spritesheetConfig.grid)
            formData.append('frames', spritesheetConfig.frames.toString())

            const response = await fetch('http://localhost:8002/extract/gif-frames', {
                method: 'POST',
                body: formData
            })

            if (!response.ok) {
                let errorMessage = 'Frame extraction failed'
                try {
                    const errorData = await response.json()
                    errorMessage = errorData.detail || errorMessage
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`
                }
                throw new Error(errorMessage)
            }

            const data = await response.json()
            console.log(`Extracted ${data.frames.length} frames from GIF (requested: ${spritesheetConfig.frames})`)
            setExtractedFrames(data.frames)

            // Initialize frame models and status based on pre-processing
            const initialFrameModels: { [key: number]: string } = {}
            const initialStatus: { [key: number]: 'pending' | 'processing' | 'completed' | 'error' } = {}
            const initialProcessedFrames: { [key: number]: any } = {}
            const initialShowProcessed: { [key: number]: boolean } = {}

            data.frames.forEach((frame: any, index: number) => {
                // Check if frame was pre-processed
                if (frame.processed && frame.model) {
                    initialFrameModels[frame.index] = frame.model
                    initialStatus[frame.index] = 'completed'
                    initialProcessedFrames[frame.index] = frame
                    initialShowProcessed[frame.index] = true // Show processed by default
                } else {
                    initialFrameModels[frame.index] = selectedModel
                    initialStatus[frame.index] = 'pending'
                    initialShowProcessed[frame.index] = false // Show original by default
                }
            })

            setFrameModels(initialFrameModels)
            setFrameProcessingStatus(initialStatus)
            setIndividualProcessedFrames(initialProcessedFrames)
            setSelectedFrameIndex(null)

            // Initialize frame selection states
            const initialSelected: { [key: number]: boolean } = {}
            data.frames.forEach((frame: any, index: number) => {
                initialSelected[frame.index] = true // All frames selected by default
            })
            setSelectedFrames(initialSelected)
            setShowProcessed(initialShowProcessed)
        } catch (err) {
            setError(`Frame extraction failed: ${err}`)
        } finally {
            setIsExtractingFrames(false)
        }
    }

    const processFramesWithModel = async () => {
        if (extractedFrames.length === 0) return

        setIsProcessingFrames(true)
        setError(null)

        try {
            if (processingMode === 'all') {
                // Process all frames with the same model
                const formData = new FormData()
                formData.append('frames_data', JSON.stringify(extractedFrames))
                formData.append('model', selectedModel)
                formData.append('grid', spritesheetConfig.grid)

                const response = await fetch('http://localhost:8002/process/frames-with-model', {
                    method: 'POST',
                    body: formData
                })

                if (!response.ok) {
                    let errorMessage = 'Frame processing failed'
                    try {
                        const errorData = await response.json()
                        errorMessage = errorData.detail || errorMessage
                    } catch (e) {
                        errorMessage = `HTTP ${response.status}: ${response.statusText}`
                    }
                    throw new Error(errorMessage)
                }

                const data = await response.json()
                setProcessedFrames(data.processed_frames)
            } else {
                // Process frames individually with their selected models
                const processedFrames: any[] = []

                for (const frame of extractedFrames) {
                    const model = frameModels[frame.index] || selectedModel

                    const formData = new FormData()
                    formData.append('frames_data', JSON.stringify([frame]))
                    formData.append('model', model)
                    formData.append('grid', spritesheetConfig.grid)

                    const response = await fetch('http://localhost:8002/process/frames-with-model', {
                        method: 'POST',
                        body: formData
                    })

                    if (!response.ok) {
                        let errorMessage = `Frame ${frame.index + 1} processing failed`
                        try {
                            const errorData = await response.json()
                            errorMessage = errorData.detail || errorMessage
                        } catch (e) {
                            errorMessage = `HTTP ${response.status}: ${response.statusText}`
                        }
                        throw new Error(errorMessage)
                    }

                    const data = await response.json()
                    processedFrames.push(data.processed_frames[0])
                }

                setProcessedFrames(processedFrames)
            }
        } catch (err) {
            setError(`Frame processing failed: ${err}`)
        } finally {
            setIsProcessingFrames(false)
        }
    }

    const updateFrameModel = (frameIndex: number, model: string) => {
        setFrameModels(prev => ({
            ...prev,
            [frameIndex]: model
        }))
    }

    const processIndividualFrame = async (frameIndex: number) => {
        const frame = extractedFrames.find(f => f.index === frameIndex)
        if (!frame) return

        const model = frameModels[frameIndex] || selectedModel

        // Update status to processing
        setFrameProcessingStatus(prev => ({
            ...prev,
            [frameIndex]: 'processing'
        }))

        try {
            const formData = new FormData()
            formData.append('frames_data', JSON.stringify([frame]))
            formData.append('model', model)
            formData.append('grid', spritesheetConfig.grid)

            const response = await fetch('http://localhost:8002/process/frames-with-model', {
                method: 'POST',
                body: formData
            })

            if (!response.ok) {
                let errorMessage = `Frame ${frameIndex + 1} processing failed`
                try {
                    const errorData = await response.json()
                    errorMessage = errorData.detail || errorMessage
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`
                }
                throw new Error(errorMessage)
            }

            const data = await response.json()

            // Update with processed frame
            setIndividualProcessedFrames(prev => ({
                ...prev,
                [frameIndex]: data.processed_frames[0]
            }))

            // Update status to completed
            setFrameProcessingStatus(prev => ({
                ...prev,
                [frameIndex]: 'completed'
            }))

        } catch (err) {
            setError(`Frame ${frameIndex + 1} processing failed: ${err}`)
            setFrameProcessingStatus(prev => ({
                ...prev,
                [frameIndex]: 'error'
            }))
        }
    }

    const selectFrame = (frameIndex: number) => {
        setSelectedFrameIndex(frameIndex)
    }

    const getProcessedFrameForIndex = (frameIndex: number) => {
        return individualProcessedFrames[frameIndex] || extractedFrames.find(f => f.index === frameIndex)
    }

    const toggleFrameSelection = (frameIndex: number) => {
        setSelectedFrames(prev => ({
            ...prev,
            [frameIndex]: !prev[frameIndex]
        }))
    }

    const toggleShowProcessed = (frameIndex: number) => {
        setShowProcessed(prev => ({
            ...prev,
            [frameIndex]: !prev[frameIndex]
        }))
    }

    const undoFrameProcessing = (frameIndex: number) => {
        setShowProcessed(prev => ({
            ...prev,
            [frameIndex]: false
        }))
        setFrameProcessingStatus(prev => ({
            ...prev,
            [frameIndex]: 'pending'
        }))
        setIndividualProcessedFrames(prev => {
            const newProcessed = { ...prev }
            delete newProcessed[frameIndex]
            return newProcessed
        })
    }

    const getDisplayFrameForIndex = (frameIndex: number) => {
        const showProcessedVersion = showProcessed[frameIndex] && individualProcessedFrames[frameIndex]
        if (showProcessedVersion) {
            return individualProcessedFrames[frameIndex]
        } else {
            // Return original frame (not processed)
            const originalFrame = extractedFrames.find(f => f.index === frameIndex)
            if (originalFrame && originalFrame.original_data) {
                // Use the stored original data
                return {
                    ...originalFrame,
                    data: originalFrame.original_data
                }
            }
            return originalFrame
        }
    }

    const getSelectedFramesForReconstruction = () => {
        return extractedFrames.filter(frame => {
            const isSelected = selectedFrames[frame.index]
            const hasProcessed = individualProcessedFrames[frame.index]
            const showProcessed = showProcessed[frame.index]

            // If frame is selected and has processed version and user wants to show processed, use processed
            // Otherwise use original
            return isSelected ? (hasProcessed && showProcessed ? individualProcessedFrames[frame.index] : frame) : null
        }).filter(Boolean)
    }

    const reconstructSpritesheet = async () => {
        // Use selected frames with their chosen versions (processed or original)
        const framesToUse = processingMode === 'individual'
            ? getSelectedFramesForReconstruction()
            : processedFrames

        if (framesToUse.length === 0) return

        setIsReconstructing(true)
        setError(null)

        try {
            const formData = new FormData()
            formData.append('frames_data', JSON.stringify(framesToUse))
            formData.append('grid', spritesheetConfig.grid)
            formData.append('filename', `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}_processed`)

            const response = await fetch('http://localhost:8002/reconstruct/spritesheet', {
                method: 'POST',
                body: formData
            })

            if (!response.ok) {
                let errorMessage = 'Spritesheet reconstruction failed'
                try {
                    const errorData = await response.json()
                    errorMessage = errorData.detail || errorMessage
                } catch (e) {
                    errorMessage = `HTTP ${response.status}: ${response.statusText}`
                }
                throw new Error(errorMessage)
            }

            const data = await response.json()

            // Convert base64 to blob
            const binaryString = atob(data.data)
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i)
            }
            const blob = new Blob([bytes], { type: 'image/png' })

            setReconstructedSpritesheet(blob)
            setReconstructedUrl(URL.createObjectURL(blob))
        } catch (err) {
            setError(`Spritesheet reconstruction failed: ${err}`)
        } finally {
            setIsReconstructing(false)
        }
    }

    const downloadReconstructedSpritesheet = () => {
        if (!reconstructedSpritesheet) return

        const url = URL.createObjectURL(reconstructedSpritesheet)
        const a = document.createElement('a')
        a.href = url
        a.download = `${uploadedFile?.name.replace(/\.[^/.]+$/, '') || 'video'}_processed_spritesheet.png`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
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

                        {/* NEW: Frame-by-Frame Processing Section */}
                        {gifUrl && (
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                                    <Palette className="w-5 h-5 mr-2" />
                                    Advanced Frame Processing
                                </h2>
                                <p className="text-gray-600 mb-6">
                                    Extract individual frames, process them one by one with different models, preview results immediately, and reconstruct the spritesheet.
                                </p>

                                {/* Step 1: Extract Frames */}
                                <div className="mb-6">
                                    <h3 className="text-lg font-medium text-gray-900 mb-3">Step 1: Extract Frames</h3>
                                    <button
                                        onClick={extractGifFrames}
                                        disabled={isExtractingFrames}
                                        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center"
                                    >
                                        {isExtractingFrames ? (
                                            <>
                                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                Extracting Frames...
                                            </>
                                        ) : (
                                            <>
                                                <Grid3x3 className="w-4 h-4 mr-2" />
                                                Extract Frames
                                            </>
                                        )}
                                    </button>
                                </div>

                                {/* Step 2: Individual Frame Processing */}
                                {extractedFrames.length > 0 && (
                                    <div className="mb-6">
                                        <h3 className="text-lg font-medium text-gray-900 mb-3">Step 2: Process Individual Frames</h3>
                                        <p className="text-sm text-gray-600 mb-4">
                                            Click on a frame to select it, choose a model, and process it individually. You can see the result immediately and try different models.
                                        </p>

                                        {/* Global Model Selection */}
                                        <div className="mb-4">
                                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                                Default Model for New Frames
                                            </label>
                                            <select
                                                value={selectedModel}
                                                onChange={(e) => setSelectedModel(e.target.value)}
                                                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            >
                                                {availableModels.map((model) => (
                                                    <option key={model.id} value={model.id}>
                                                        {model.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>
                                )}

                                {/* Step 3: Reconstruct Spritesheet */}
                                {(processedFrames.length > 0 || Object.values(selectedFrames).some(selected => selected)) && (
                                    <div className="mb-6">
                                        <h3 className="text-lg font-medium text-gray-900 mb-3">Step 3: Reconstruct Spritesheet</h3>
                                        <button
                                            onClick={reconstructSpritesheet}
                                            disabled={isReconstructing}
                                            className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center"
                                        >
                                            {isReconstructing ? (
                                                <>
                                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                                    Reconstructing...
                                                </>
                                            ) : (
                                                <>
                                                    <Grid3x3 className="w-4 h-4 mr-2" />
                                                    Reconstruct Spritesheet
                                                </>
                                            )}
                                        </button>
                                    </div>
                                )}

                                {/* Results */}
                                {reconstructedUrl && (
                                    <div className="border-t pt-6">
                                        <h3 className="text-lg font-medium text-gray-900 mb-3">Final Result</h3>
                                        <div className="space-y-4">
                                            <img
                                                src={reconstructedUrl}
                                                alt="Reconstructed Spritesheet"
                                                className="max-w-full h-auto rounded-lg border border-gray-200"
                                            />
                                            <button
                                                onClick={downloadReconstructedSpritesheet}
                                                className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center"
                                            >
                                                <Download className="w-4 h-4 mr-2" />
                                                Download Processed Spritesheet
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* Frame Preview */}
                                {extractedFrames.length > 0 && (
                                    <div className="border-t pt-6">
                                        <h3 className="text-lg font-medium text-gray-900 mb-3">
                                            Frame Processing & Selection ({extractedFrames.length} frames)
                                        </h3>
                                        <p className="text-sm text-gray-600 mb-4">
                                            Click frames to process them. Toggle between original/processed views. Select which frames to include in the final spritesheet.
                                        </p>

                                        {/* Selected Frame Preview */}
                                        {selectedFrameIndex !== null && (
                                            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                                                <h4 className="text-md font-medium text-gray-900 mb-3">
                                                    Frame {selectedFrameIndex + 1} - Side by Side Comparison
                                                </h4>
                                                <div className="grid grid-cols-2 gap-4 mb-4">
                                                    {/* Original Frame */}
                                                    <div className="text-center">
                                                        <img
                                                            src={`data:image/png;base64,${extractedFrames.find(f => f.index === selectedFrameIndex)?.original_data || extractedFrames.find(f => f.index === selectedFrameIndex)?.data}`}
                                                            alt={`Original Frame ${selectedFrameIndex + 1}`}
                                                            className="w-full h-32 object-cover rounded border border-gray-200"
                                                        />
                                                        <p className="text-xs text-gray-600 mt-1">Original</p>
                                                    </div>

                                                    {/* Processed Frame */}
                                                    <div className="text-center">
                                                        <img
                                                            src={`data:image/png;base64,${getDisplayFrameForIndex(selectedFrameIndex).data}`}
                                                            alt={`Processed Frame ${selectedFrameIndex + 1}`}
                                                            className="w-full h-32 object-cover rounded border border-gray-200"
                                                        />
                                                        <p className="text-xs text-gray-600 mt-1">
                                                            {individualProcessedFrames[selectedFrameIndex] ? 'Processed' : 'No processing yet'}
                                                        </p>
                                                    </div>
                                                </div>

                                                {/* Controls */}
                                                <div className="space-y-3">
                                                    <div className="flex gap-2">
                                                        <div className="flex-1">
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                Model:
                                                            </label>
                                                            <select
                                                                value={frameModels[selectedFrameIndex] || selectedModel}
                                                                onChange={(e) => updateFrameModel(selectedFrameIndex, e.target.value)}
                                                                className="w-full p-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                                            >
                                                                {availableModels.map((model) => (
                                                                    <option key={model.id} value={model.id}>
                                                                        {model.name}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </div>
                                                        <div className="flex-1">
                                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                                Actions:
                                                            </label>
                                                            <div className="flex gap-2">
                                                                <button
                                                                    onClick={() => processIndividualFrame(selectedFrameIndex)}
                                                                    disabled={frameProcessingStatus[selectedFrameIndex] === 'processing'}
                                                                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white px-3 py-2 rounded text-sm font-medium transition-colors flex items-center justify-center"
                                                                >
                                                                    {frameProcessingStatus[selectedFrameIndex] === 'processing' ? (
                                                                        <>
                                                                            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-1"></div>
                                                                            Processing...
                                                                        </>
                                                                    ) : (
                                                                        'Process'
                                                                    )}
                                                                </button>
                                                                {individualProcessedFrames[selectedFrameIndex] && (
                                                                    <button
                                                                        onClick={() => undoFrameProcessing(selectedFrameIndex)}
                                                                        className="flex-1 bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded text-sm font-medium transition-colors"
                                                                    >
                                                                        Undo
                                                                    </button>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {individualProcessedFrames[selectedFrameIndex] && (
                                                        <div className="flex gap-2">
                                                            <button
                                                                onClick={() => toggleShowProcessed(selectedFrameIndex)}
                                                                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${showProcessed[selectedFrameIndex]
                                                                    ? 'bg-blue-600 text-white'
                                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                                    }`}
                                                            >
                                                                {showProcessed[selectedFrameIndex] ? 'Show Processed' : 'Show Original'}
                                                            </button>
                                                            <button
                                                                onClick={() => toggleFrameSelection(selectedFrameIndex)}
                                                                className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-colors ${selectedFrames[selectedFrameIndex]
                                                                    ? 'bg-green-600 text-white'
                                                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                                                                    }`}
                                                            >
                                                                {selectedFrames[selectedFrameIndex] ? 'Include in Spritesheet' : 'Exclude from Spritesheet'}
                                                            </button>
                                                        </div>
                                                    )}

                                                    {frameProcessingStatus[selectedFrameIndex] === 'error' && (
                                                        <p className="text-xs text-red-600">Processing failed</p>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* Frame Grid */}
                                        <div className="grid grid-cols-4 md:grid-cols-6 gap-3 max-h-96 overflow-y-auto">
                                            {extractedFrames.map((frame, index) => {
                                                const isSelected = selectedFrameIndex === frame.index
                                                const status = frameProcessingStatus[frame.index] || 'pending'
                                                const isProcessed = status === 'completed'
                                                const isFrameSelected = selectedFrames[frame.index]
                                                const showProcessedVersion = showProcessed[frame.index] && individualProcessedFrames[frame.index]

                                                return (
                                                    <div
                                                        key={index}
                                                        className={`relative bg-white rounded-lg border-2 p-2 cursor-pointer transition-all ${isSelected
                                                            ? 'border-blue-500 shadow-md'
                                                            : isProcessed
                                                                ? 'border-green-500'
                                                                : 'border-gray-200 hover:border-gray-300'
                                                            }`}
                                                        onClick={() => selectFrame(frame.index)}
                                                    >
                                                        <img
                                                            src={`data:image/png;base64,${getDisplayFrameForIndex(frame.index).data}`}
                                                            alt={`Frame ${index + 1}`}
                                                            className="w-full h-16 object-cover rounded border border-gray-200 mb-1"
                                                        />
                                                        <div className="text-xs text-center text-gray-600 mb-1">
                                                            Frame {index + 1}
                                                        </div>
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex items-center">
                                                                {status === 'processing' && (
                                                                    <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-500"></div>
                                                                )}
                                                                {status === 'completed' && (
                                                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                                                )}
                                                                {status === 'error' && (
                                                                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                                                )}
                                                                {status === 'pending' && (
                                                                    <div className="w-3 h-3 bg-gray-300 rounded-full"></div>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center">
                                                                {isFrameSelected && (
                                                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                                                )}
                                                                {showProcessedVersion && (
                                                                    <div className="w-2 h-2 bg-blue-500 rounded-full ml-1"></div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                )
                                            })}
                                        </div>

                                        {/* Summary */}
                                        <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                                            <div className="text-sm text-gray-600">
                                                <strong>Summary:</strong> {Object.values(selectedFrames).filter(Boolean).length} frames selected for spritesheet,
                                                {Object.keys(individualProcessedFrames).length} frames processed
                                            </div>
                                        </div>
                                    </div>
                                )}
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
                                    <li>6. <strong>NEW:</strong> Use Advanced Frame Processing - click frames to process individually with immediate preview!</li>
                                </ol>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
