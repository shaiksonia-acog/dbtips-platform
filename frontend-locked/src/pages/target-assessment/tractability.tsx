import Plot from 'react-plotly.js';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import LoadingButton from '../../components/loading';
import { Empty } from 'antd';
// import json from '../../assets/ADORA3.json';
// const data = json.target_prioritisation.tractability;

const Tractability = ({ target }) => {
	const payload = {
		target: target,
	};

	const {
		data: tractabilityData,
		error: tractabilityError,
		isLoading: tractabilityLoading,
	} = useQuery(
		['tractability', payload],
		() => fetchData(payload, '/target-assessment/tractability/'),
		{
			enabled: !!target,
		}
	);

	const updated = {};

	const colors = {
		true: '#93d2fc',
		false: '#ccc',
	};

	for (const key in tractabilityData?.tractability) {
		const arr = [];
		const element = tractabilityData.tractability[key];

		for (const key in element.Items) {
			const item = element.Items[key];
			arr.push({ label: key, value: item.Value });
		}

		updated[key] = arr;
	}

	return (
		<section id='tractability' className='px-[5vw] py-20 bg-gray-50 mt-12'>
			<h1 className='text-3xl font-semibold'>Tractability</h1>
			<p className='italic font-medium mt-2'>
				The likelihood of identifying a modulator that interacts effectively
				with the target/domain (or pathway). This aids in understanding the
				ability of a protein to bind a drug-like modulator.
			</p>

			{tractabilityLoading ? (
				<LoadingButton />
			) : tractabilityError ? (
				<div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
					<Empty />
				</div>
			) : (
				<div className='mt-5 flex items-center justify-center'>
					{Object.keys(updated).map((mod) => {
						const items = updated[mod];
						if (!items.length) return null;

						const labels = items.map((item) => item.label);
						const values = items.map(() => 1);
						const barColors = items.map((item) => colors[item.value]);

						return (
							<Plot
								key={mod}
								data={[
									{
										x: values,
										// y: labels,
										type: 'bar',
										orientation: 'h',
										text: labels,
										hoverinfo: 'none',
										// textposition: 'inside', // Labels inside the bars
										insidetextanchor: 'middle', // Center the labels
										marker: {
											color: barColors,
										},
									},
								]}
								layout={{
									title: {
										text: mod,
										font: { size: 16 },
									},
									xaxis: {
										visible: true,
										title: mod,
										range: [0, 1],
									},
									yaxis: { visible: false, automargin: true },
									height: 400,
									width: 300,
									margin: { t: 50, b: 50, l: 50 },
									showlegend: false,
									shapes: [
										{
											type: 'rect',
											xref: 'paper',
											yref: 'paper',
											x0: 0,
											y0: 0,
											x1: 1,
											y1: 1,
											line: {
												color: 'black',
												width: 1,
											},
										},
									],
								}}
								config={{ displayModeBar: false }}
							/>
						);
					})}
				</div>
			)}
		</section>
	);
};

export default Tractability;
