import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000, // 30 seconds for image processing
    headers: {
        'Content-Type': 'application/json',
    },
})

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

        const response = await api.post('/process/spritesheet', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })

        return response.data
    },
}
