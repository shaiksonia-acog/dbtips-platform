import { AgGridReact } from 'ag-grid-react';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import { Empty } from 'antd';

const Paralogs = ({ target,  }) => {
	const payload = {
		target: target,
	};

	const { data: paralogsData, error: paralogsError } = useQuery(
		['paralogs', payload],
		() => fetchData(payload, '/target-assessment/paralogs/'),
		{
			enabled: !!target ,
		}
	);

	// Fallback to empty array if data is null or undefined
	const rowData = [];

	if (paralogsData) {
		for (const key in paralogsData.paralogs) {
			const elements = paralogsData.paralogs[key];
			rowData.push(...elements);
		}
	}

	// console.log(rowData);

	// Check if rowData is empty before generating column definitions
	const defs =
		rowData.length > 0
			? Object.keys(rowData[0]).map((key) => {
					const def: any = { field: key }; // Type assertion to allow cellRenderer

					if (key === 'Paralog Pair URL') {
						def.cellRenderer = (params: any) =>
							params.value ? (
								<a target='_blank' href={params.value}>
									expression data
								</a>
							) : null;
					}

					if (key == 'Common GO slim') {
						def.minWidth = 540;
					}

					return def;
			  })
			: [];

	console.log(defs);

	return (
		<section id='paralogs' className='mt-12 px-[5vw]'>
			<h1 className='text-3xl font-semibold'>Paralogs</h1>
			<p className='mt-2 italic font-medium'>
				Homology for a target across selected species. Understanding paralogs
				can help avoid off-target effects and improve drug specificity.
			</p>

			{paralogsError ? (
				// Error div with same height as AgGrid
				<div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
					<Empty />
				</div>
			) : (
				<div className='ag-theme-quartz mt-4 h-[80vh] max-h-[720px]'>
					<AgGridReact
						defaultColDef={{
							minWidth: 150,
							flex: 1,
							filter: true,
							sortable: true,
							floatingFilter: true,
							headerClass: 'font-semibold px-6 py-1',
							autoHeaderHeight: true,
							wrapHeaderText: true,
						}}
						columnDefs={defs}
						rowData={paralogsData ? rowData : null}
						pagination={true}
					/>
				</div>
			)}
		</section>
	);
};

export default Paralogs;
