import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

console.log('API_BASE_URL:', API_BASE_URL) // Debug log

export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 120000, // 2 minutes for spritesheet processing with all models
})

// Add request interceptor for debugging
api.interceptors.request.use(
    (config) => {
        const timestamp = new Date().toISOString()
        console.log(`🚀 [${timestamp}] API REQUEST:`, {
            method: config.method?.toUpperCase(),
            url: (config.baseURL || '') + (config.url || ''),
            headers: config.headers,
            data: config.data instanceof FormData ? 'FormData' : config.data
        })
        return config
    },
    (error) => {
        console.error('❌ REQUEST ERROR:', error)
        return Promise.reject(error)
    }
)

// Add response interceptor for debugging
api.interceptors.response.use(
    (response) => {
        const timestamp = new Date().toISOString()
        console.log(`✅ [${timestamp}] API RESPONSE:`, {
            status: response.status,
            url: response.config.url,
            dataSize: JSON.stringify(response.data).length,
            data: response.data
        })
        return response
    },
    (error) => {
        const timestamp = new Date().toISOString()
        console.error(`❌ [${timestamp}] API ERROR:`, {
            status: error.response?.status,
            message: error.message,
            url: error.config?.url,
            data: error.response?.data
        })
        return Promise.reject(error)
    }
)

// API endpoints
export const endpoints = {
    health: '/health',
    remove: '/remove',
    upload: '/upload',
    projects: '/projects',
} as const

// Types
export interface HealthResponse {
    ok: boolean
}

export interface RemoveResponse {
    success: boolean
    message?: string
    downloadUrl?: string
}

export interface ModelResult {
    success: boolean
    data?: string // base64 encoded image
    size?: number
    error?: string
}

export interface AllModelsResponse {
    original_filename: string
    original_size: number
    models: {
        [modelName: string]: ModelResult
    }
}

export interface SpritesheetAllModelsResponse {
    original_filename: string
    original_size: number
    spritesheet_size: string
    grid: string
    frames_processed: number
    frame_size: string
    models: {
        [modelName: string]: ModelResult & {
            frames_processed?: number
        }
    }
}

export interface SpritesheetConfig {
    grid: string // e.g., "5x2"
    frames?: number
    frameWidth?: number
    frameHeight?: number
}

export interface SpritesheetResponse {
    success: boolean
    message?: string
    frames?: string[]
    spritesheetUrl?: string
    config: SpritesheetConfig
}

export interface VideoAnalysisResponse {
    filename: string
    analysis: {
        duration: number
        fps: number
        size: [number, number]
        total_frames: number
        recommended_fps: number
        recommended_duration: number
        recommended_frames: number
        file_size: number
    }
}

export interface VideoToGifConfig {
    fps: number
    duration?: number
    maxWidth: number
    maxHeight: number
}

export interface VideoPipelineConfig {
    fps: number
    duration?: number
    grid: string
    frames?: number
    model: string
    allModels: boolean
    keepIntermediates: boolean
}

// API functions
export const apiClient = {
    // Health check
    async health(): Promise<HealthResponse> {
        const response = await api.get(endpoints.health)
        return response.data
    },

    // Single image processing
    async removeBackground(file: File): Promise<RemoveResponse> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post(endpoints.remove, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            responseType: 'blob',
        })

        // Create download URL for the processed image
        const blob = new Blob([response.data], { type: 'image/png' })
        const downloadUrl = URL.createObjectURL(blob)

        return {
            success: true,
            downloadUrl,
        }
    },

    // Process with all models
    async removeBackgroundAllModels(file: File): Promise<AllModelsResponse> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('/remove-all-models', formData)

        return response.data
    },

    // Process spritesheet with all models
    async processSpritesheetAllModels(
        file: File,
        config: SpritesheetConfig
    ): Promise<SpritesheetAllModelsResponse> {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('grid', config.grid)
        if (config.frames) {
            formData.append('frames', config.frames.toString())
        }
        if (config.frameWidth) {
            formData.append('frameWidth', config.frameWidth.toString())
        }
        if (config.frameHeight) {
            formData.append('frameHeight', config.frameHeight.toString())
        }

        const response = await api.post('/process/spritesheet-all-models', formData)

        return response.data
    },

    // Spritesheet processing
    async processSpritesheet(
        file: File,
        config: SpritesheetConfig
    ): Promise<SpritesheetResponse> {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('grid', config.grid)
        if (config.frames) {
            formData.append('frames', config.frames.toString())
        }
        if (config.frameWidth) {
            formData.append('frameWidth', config.frameWidth.toString())
        }
        if (config.frameHeight) {
            formData.append('frameHeight', config.frameHeight.toString())
        }

        const response = await api.post('/process/spritesheet', formData)

        return response.data
    },

    // GIF to spritesheet processing
    async processGifToSpritesheet(
        file: File,
        config: SpritesheetConfig
    ): Promise<SpritesheetResponse> {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('grid', config.grid)
        if (config.frames) {
            formData.append('frames', config.frames.toString())
        }
        if (config.frameWidth) {
            formData.append('frameWidth', config.frameWidth.toString())
        }
        if (config.frameHeight) {
            formData.append('frameHeight', config.frameHeight.toString())
        }

        const response = await api.post('/process/gif-to-spritesheet', formData)

        return response.data
    },

    // Video analysis
    async analyzeVideo(file: File): Promise<VideoAnalysisResponse> {
        const formData = new FormData()
        formData.append('file', file)

        const response = await api.post('/analyze/video', formData)
        return response.data
    },

    // Video to GIF conversion
    async videoToGif(file: File, config: VideoToGifConfig): Promise<Blob> {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('fps', config.fps.toString())
        if (config.duration) {
            formData.append('duration', config.duration.toString())
        }
        formData.append('max_width', config.maxWidth.toString())
        formData.append('max_height', config.maxHeight.toString())

        const response = await api.post('/process/video-to-gif', formData, {
            responseType: 'blob'
        })

        return response.data
    },

    // Video pipeline processing
    async processVideoPipeline(file: File, config: VideoPipelineConfig): Promise<any> {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('fps', config.fps.toString())
        if (config.duration) {
            formData.append('duration', config.duration.toString())
        }
        formData.append('grid', config.grid)
        if (config.frames) {
            formData.append('frames', config.frames.toString())
        }
        formData.append('model', config.model)
        formData.append('all_models', config.allModels.toString())
        formData.append('keep_intermediates', config.keepIntermediates.toString())

        const response = await api.post('/process/video-pipeline', formData)
        return response.data
    },
}
