/// <reference types="vite/client" />
/// <reference types="@modyfi/vite-plugin-yaml/modules"/>
/// <reference types='vite-plugin-svgr/client' />

interface ImportMetaEnv {
	readonly VITE_API_URI: string;
	// Add other Vite-specific environment variables here
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
