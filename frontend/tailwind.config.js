/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Noto Sans JP', 'Hiragino Kaku Gothic ProN', 'Meiryo', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
