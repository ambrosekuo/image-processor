export function Footer() {
    return (
        <footer className="bg-white border-t">
            <div className="container mx-auto px-4 py-8">
                <div className="grid md:grid-cols-4 gap-8">
                    <div>
                        <h3 className="text-lg font-semibold mb-4">bgremove</h3>
                        <p className="text-gray-600 text-sm">
                            AI-powered background removal tool for images and spritesheets.
                        </p>
                    </div>

                    <div>
                        <h4 className="font-semibold mb-4">Features</h4>
                        <ul className="space-y-2 text-sm text-gray-600">
                            <li>Single Image Processing</li>
                            <li>Spritesheet Processing</li>
                            <li>Batch Operations</li>
                            <li>Real-time Preview</li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-semibold mb-4">Use Cases</h4>
                        <ul className="space-y-2 text-sm text-gray-600">
                            <li>Game Development</li>
                            <li>Web Design</li>
                            <li>Content Creation</li>
                            <li>E-commerce</li>
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-semibold mb-4">Support</h4>
                        <ul className="space-y-2 text-sm text-gray-600">
                            <li>Documentation</li>
                            <li>API Reference</li>
                            <li>GitHub</li>
                            <li>Contact</li>
                        </ul>
                    </div>
                </div>

                <div className="border-t mt-8 pt-8 text-center text-sm text-gray-500">
                    <p>&copy; 2024 bgremove. Built with Next.js and FastAPI.</p>
                </div>
            </div>
        </footer>
    )
}
