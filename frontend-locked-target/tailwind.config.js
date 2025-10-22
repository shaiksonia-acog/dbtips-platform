/** @type {import('tailwindcss').Config} */
export default {
	content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
	theme: {
		extend: {
		  fontWeight: {
			medium: '400', // Change semibold to normal weight
		  },
		  
		},
	  },
	plugins: [],
};
