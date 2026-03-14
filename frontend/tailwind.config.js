/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'di-bg': '#0A1F1A',
                'di-card': '#112820',
                'di-accent': '#00C896',
                'di-accent-dim': '#00A87A',
                'di-text': '#FFFFFF',
                'di-text-secondary': '#8BA89E',
                'di-warning': '#F59E0B',
                'di-severity-high': '#EF4444',
                'di-severity-medium': '#F59E0B',
                'di-severity-low': '#10B981',
                'di-border': '#1E3A2F',
            },
            fontFamily: {
                'inter': ['Inter', 'system-ui', 'sans-serif'],
            },
            spacing: {
                '18': '4.5rem',
                '88': '22rem',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'fade-in': 'fadeIn 0.5s ease-out',
                'slide-up': 'slideUp 0.3s ease-out',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                slideUp: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                },
            },
        },
    },
    plugins: [],
};
