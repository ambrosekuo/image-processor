'use client'

import { useState } from 'react'
import { FolderOpen, Plus, Grid, Download, Trash2 } from 'lucide-react'
import Link from 'next/link'

interface Project {
    id: string
    name: string
    type: 'single' | 'spritesheet'
    createdAt: string
    status: 'completed' | 'processing' | 'failed'
    files: string[]
}

// Mock data - in a real app, this would come from an API
const mockProjects: Project[] = [
    {
        id: '1',
        name: 'Character Walk Animation',
        type: 'spritesheet',
        createdAt: '2024-01-15',
        status: 'completed',
        files: ['character_walk_processed.png', 'frame_001.png', 'frame_002.png']
    },
    {
        id: '2',
        name: 'Bear Boss Spritesheet',
        type: 'spritesheet',
        createdAt: '2024-01-14',
        status: 'completed',
        files: ['bear_boss_processed.png']
    },
    {
        id: '3',
        name: 'Logo Background Removal',
        type: 'single',
        createdAt: '2024-01-13',
        status: 'completed',
        files: ['logo_no_bg.png']
    }
]

export default function ProjectsPage() {
    const [projects] = useState<Project[]>(mockProjects)

    return (
        <div className="max-w-6xl mx-auto">
            <div className="mb-8">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
                        <p className="text-gray-600 mt-2">
                            Manage your processed images and spritesheets.
                        </p>
                    </div>
                    <Link
                        href="/upload"
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" />
                        New Project
                    </Link>
                </div>
            </div>

            {projects.length === 0 ? (
                <div className="text-center py-12">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <FolderOpen className="w-8 h-8 text-gray-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No Projects Yet</h3>
                    <p className="text-gray-600 mb-6">
                        Start by uploading an image or spritesheet to create your first project.
                    </p>
                    <div className="flex gap-4 justify-center">
                        <Link
                            href="/upload"
                            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                        >
                            Upload Image
                        </Link>
                        <Link
                            href="/spritesheet"
                            className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
                        >
                            Process Spritesheet
                        </Link>
                    </div>
                </div>
            ) : (
                <div className="grid gap-6">
                    {projects.map((project) => (
                        <div key={project.id} className="bg-white rounded-lg border p-6 hover:shadow-md transition-shadow">
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2">
                                        <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${project.status === 'completed'
                                                ? 'bg-green-100 text-green-700'
                                                : project.status === 'processing'
                                                    ? 'bg-blue-100 text-blue-700'
                                                    : 'bg-red-100 text-red-700'
                                            }`}>
                                            {project.status}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
                                        <div className="flex items-center gap-1">
                                            {project.type === 'spritesheet' ? (
                                                <Grid className="w-4 h-4" />
                                            ) : (
                                                <FolderOpen className="w-4 h-4" />
                                            )}
                                            <span className="capitalize">{project.type}</span>
                                        </div>
                                        <span>Created {new Date(project.createdAt).toLocaleDateString()}</span>
                                        <span>{project.files.length} file{project.files.length !== 1 ? 's' : ''}</span>
                                    </div>

                                    <div className="flex flex-wrap gap-2">
                                        {project.files.slice(0, 3).map((file, index) => (
                                            <span
                                                key={index}
                                                className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                                            >
                                                {file}
                                            </span>
                                        ))}
                                        {project.files.length > 3 && (
                                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                                +{project.files.length - 3} more
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 ml-4">
                                    <button className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                                        <Download className="w-4 h-4" />
                                    </button>
                                    <button className="p-2 text-gray-400 hover:text-red-600 transition-colors">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
