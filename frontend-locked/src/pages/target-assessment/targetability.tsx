import Plot from 'react-plotly.js';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import LoadingButton from '../../components/loading';
import { Empty } from 'antd';
// import json from '../../assets/ADORA3.json';

// const response = json.target_prioritisation.targetability;

const Targetability = ({ target,  }) => {
	const payload = {
		target: target,
		
	};

	const {
		data: targetabilityData,
		error: targetabilityError,
		isLoading: targetabilityLoading,
	} = useQuery(
		['targetability', payload],
		() => fetchData(payload, '/target-assessment/targetability/'),
		{
			enabled: !!target ,
		}
	);
	const allKeys = [];
	const allValues = [];

	for (const key in targetabilityData?.targetability?.Prioritisation) {
		allKeys.push(key);
		if (targetabilityData.targetability.Prioritisation[key] == 'no data')
			allValues.push(null);
		else allValues.push(targetabilityData.targetability.Prioritisation[key]);
	}

	return (
		<section id='targetability' className='mt-12 px-[5vw]'>
			<h1 className='text-3xl font-semibold'>Targetability</h1>
			<p className='italic font-medium mt-2'>
				The section is designed to visually inform on target prioritisation
				providing information to help users assess the targets for further
				prioritisation or deprioritisation.
			</p>

			{targetabilityLoading ? (
				<LoadingButton />
			) : targetabilityError ? (
				<div className='mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
					<Empty />
				</div>
			) : 
			!targetabilityData ? (
				<div className='mt-4 h-[280px] flex items-center justify-center'>
					<Empty description='No data' />
				</div>
			) :
			(
				<div>
					<div className='flex items-center justify-center mt-4 gap-x-4'>
						<div className='flex items-center gap-x-2'>
							<div className='w-5 h-5 bg-[#93d2fc] border border-black'></div>
							<span>Favourable</span>
						</div>
						<div className='flex items-center gap-x-2'>
							<div className='w-5 h-5 bg-[#003f6a] border border-black'></div>
							<span>Unfavourable</span>
						</div>
						<div className='flex items-center gap-x-2'>
							<div className='w-5 h-5 bg-[white] border border-black'></div>
							<span>No evidence</span>
						</div>
					</div>

					<div className='flex items-center justify-center'>
						<Plot
							data={[
								{
									z: [allValues],
									x: allKeys,
									y: [targetabilityData?.targetability?.['Approved Symbol']],
									type: 'heatmap',
									colorscale: [
										[0, '#003f6a'],
										[1, '#93d2fc'],
									],
									zmin: -1,
									zmax: 1,
									showscale: true,
									colorbar: {
										title: 'Value',
									},
									// Add gap between cells
									xgap: 1, // Gap between cells along the x-axis
									ygap: 1, // Gap between cells along the y-axis
								},
							]}
							layout={{
								title: 'Target Prioritisation Heatmap',
								xaxis: {
									title: 'Prioritisation Features',
									automargin: true,
								},
								yaxis: {
									title: 'Approved Symbol',
									automargin: true,
								},
								width: 1240,
								height: 300,
							}}
							config={{ displayModeBar: false }} // Optional: remove plotly mode bar
						/>
					</div>
				</div>
			)}
		</section>
	);
};

export default Targetability;
