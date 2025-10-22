const Footer = () => {
	return (
			<footer className='text-[8px] md:text-sm mt-1.5 pb-2'>
			<p className='text-center text-xs'>
				&copy; Copyright 2025 Aganitha AI Inc. All Rights Reserved.
			</p>

			<p className='mt-1 text-xs text-center mx-36'>
				AI can make mistakes. Verify critical information independently. Not intended to produce
				treatment or legal advice. Note that your inputs are transmitted via AWS cloud servers to OpenAI, Perplexity and 
				Google&lsquo;s LLM models. Please see the data privacy policy of {' '}
				<a
					href='https://help.openai.com/en/articles/5722486-how-your-data-is-used-to-improve-model-performance'
					target='_blank'
					rel='noopener noreferrer'
					className='underline text-primary'
				>
					OpenAI
				</a>{", "}
				<a
					href='https://docs.perplexity.ai/guides/privacy-security'
					target='_blank'
					rel='noopener noreferrer'
					className='underline text-primary'
				>
					Perplexity
				</a>{" and "}
				
				<a
					href='https://cloud.google.com/gemini/docs/discover/data-governance'
					target='_blank'
					rel='noopener noreferrer'
					className='underline text-primary'
				>
					Google
				</a>{' '}
				to understand how your data is handled
			</p>

			<p className='mt-1 text-center'>
				For support or feedback, contact us at{' '}
				<a
					target='_blank'
					rel='noopener noreferrer'
					href='mailto:igniva-desk@aganitha.ai'
					className='underline text-primary'
				>
					igniva-desk@aganitha.ai
				</a>
			</p>
		</footer>
	);
};

export default Footer;
