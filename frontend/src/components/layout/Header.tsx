'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Palette, Upload, Grid, FolderOpen, Video, Image, Zap } from 'lucide-react'

const navigation = [
    { name: 'Home', href: '/', icon: Palette },
    { name: 'Pipeline', href: '/pipeline', icon: Zap },
    { name: 'Upload', href: '/upload', icon: Upload },
    { name: 'Spritesheet', href: '/spritesheet', icon: Grid },
    { name: 'GIF to Spritesheet', href: '/gif-to-spritesheet', icon: Image },
    { name: 'Video', href: '/video', icon: Video },
    { name: 'Projects', href: '/projects', icon: FolderOpen },
]

export function Header() {
    const pathname = usePathname()

    return (
        <header className="bg-white shadow-sm border-b">
            <div className="container mx-auto px-4">
                <div className="flex items-center justify-between h-16">
                    <div className="flex items-center space-x-8">
                        <Link href="/" className="flex items-center space-x-2">
                            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                                <Palette className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-bold text-gray-900">sprite-processor</span>
                        </Link>

                        <nav className="hidden md:flex space-x-1">
                            {navigation.map((item) => {
                                const isActive = pathname === item.href
                                return (
                                    <Link
                                        key={item.name}
                                        href={item.href}
                                        className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${isActive
                                            ? 'bg-blue-100 text-blue-700'
                                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                                            }`}
                                    >
                                        <item.icon className="w-4 h-4" />
                                        <span>{item.name}</span>
                                    </Link>
                                )
                            })}
                        </nav>
                    </div>

                    <div className="flex items-center space-x-4">
                        <span className="text-sm text-gray-500">Complete Sprite Processing Pipeline</span>
                    </div>
                </div>
            </div>
        </header>
    )
}
