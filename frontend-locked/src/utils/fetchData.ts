export const fetchData = async (payload, endpoint) => {
	const response = await fetch(`${import.meta.env.VITE_API_URI}${endpoint}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(payload),
	});

	if (!response.ok) {
		// Attempt to parse the error response
		const errorText = await response.text(); // Using .text() to handle non-JSON responses too
		let errorMessage;
		try {
			// Try to parse as JSON
			const errorData = JSON.parse(errorText);
			errorMessage = errorData.message || JSON.stringify(errorData);
		} catch {
			// Fallback to plain text if not JSON
			errorMessage = errorText;
		}
		throw new Error(errorMessage || 'An unknown error occurred');
	}

	// Return the appropriate data based on the endpoint
	return endpoint === '/export' ? response.blob() : response.json();
};
