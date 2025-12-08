/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                // "Digital Harmony" Palette
                dhg: {
                    nav: '#0F172A',     // Deep Navy (Stability)
                    primary: '#3B82F6', // Innovation Blue
                    accent: '#8B5CF6',  // Creative Purple
                    orange: '#FF6B35',  // DHG Orange (CTA)
                    success: '#10B981', // Growth Green

                    // Warm Neutrals (Humanity/Canvas)
                    surface: '#FAF9F6',   // Warm Off-White (matches interface)
                    paper: '#FFFFFF',   // Pure White
                    text: '#1E293B',    // Slate Gray (Softer than black)
                    muted: '#64748B',   // Muted Text
                }
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                serif: ['Merriweather', 'serif'], // For "inspiring" text
            },
            animation: {
                'wave': 'wave 3s ease-in-out infinite',
                'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
            },
            keyframes: {
                wave: {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-5px)' },
                }
            }
        },
    },
    plugins: [],
}
