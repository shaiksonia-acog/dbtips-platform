import { useState, useEffect } from 'react';
import Targetability from './targetability';
import Tractability from './tractability';
import Paralogs from './paralogs';
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../../utils/parseUrlParams';
import GeneEssentialityMap from './geneMap';
const TargetAssessment = () => {
	const location = useLocation();
	const [target, setTarget] = useState('');

	useEffect(() => {
		const queryParams = new URLSearchParams(location.search);
		const { target } = parseQueryParams(queryParams);
		setTarget(target?.split('(')[0]);
	}, [location]);
	
	return (
		<section>
			<Targetability target={target}  />
			<Tractability target={target}  />
			<Paralogs target={target}  />
			<div className='px-[5vw]'>

			<GeneEssentialityMap  
			target={target}
		/>
			</div>
		</section>
	);
};

export default TargetAssessment;
