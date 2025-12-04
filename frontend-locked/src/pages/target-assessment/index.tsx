import { useState, useEffect } from 'react';
import Targetability from './targetability';
import Tractability from './tractability';
// import Paralogs from './paralogs';
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../../utils/parseUrlParams';
import GeneEssentialityMap from './geneMap';
import Orthologs from './orthologs';
import { matchesPattern } from '../../utils/helper';
const TargetAssessment = () => {
	const location = useLocation();
	const [target, setTarget] = useState('');

	useEffect(() => {
		const queryParams = new URLSearchParams(location.search);
		const { target } = parseQueryParams(queryParams);
		setTarget(target?.split('(')[0]);
	}, [location]);
	
	const isRNA = matchesPattern(target || "");
	return (
		<section>
			{!isRNA &&<Targetability target={target}  />}
			{!isRNA &&<Tractability target={target}  />}
			{/* <Paralogs target={target}  /> */}
			<Orthologs target={target}  />
			<div className='px-[5vw]'>

			<GeneEssentialityMap  
			target={target}
		/>

			</div>
		</section>
	);
};

export default TargetAssessment;
