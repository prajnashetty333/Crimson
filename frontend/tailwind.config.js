/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#8B5CF6',
          light: '#C4B5FD',
          dark: '#7C3AED',
        },
        lavender: '#C4B5FD',
        pinkSoft: '#FBCFE8',
        calmBg: '#F5F3FF',
        wellnessWhite: '#FAFAFA',
        successSoft: '#86EFAC',
        warningSoft: '#FDE68A',
        alertSoft: '#FDA4AF',
        analyticsBlue: '#93C5FD',
        textPrimary: '#1F2937',
        textSecondary: '#6B7280',
        textLight: '#9CA3AF',
      },
      fontFamily: {
        sans: ['Poppins', 'Inter', 'sans-serif'],
      },
      borderRadius: {
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 10px 25px -5px rgba(139, 92, 246, 0.05), 0 8px 10px -6px rgba(139, 92, 246, 0.05)',
        'premium': '0 20px 40px -15px rgba(139, 92, 246, 0.15)',
      }
    },
  },
  plugins: [],
}
