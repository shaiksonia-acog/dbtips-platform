import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import svgr from 'vite-plugin-svgr';
import ViteYaml from '@modyfi/vite-plugin-yaml';

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		ViteYaml(),
		react(),
		svgr({
			svgrOptions: {
				svgProps: { fill: '#6b6b6b' },
				icon: true,
			},
		}),
	],
	server: {
		port: 3000,
	},
});
