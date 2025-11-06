import { AgGridReact } from 'ag-grid-react';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import { ConfigProvider, Empty, Segmented } from 'antd';
import CustomHeader from '../../components/customHeader';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useMemo, useState } from 'react';
import { ChartLine, List } from 'lucide-react';
interface SpeciesDataItem {
    "Identity Score": string | number | null | undefined; // It must be one of these since you are using Number() on it
    [key: string]: any;
}
const Paralogs = ({ target }) => {
	const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
	const showClusters = true;	
	
	const payload = {
		target: target,
	};

	const { data: paralogsData, error: paralogsError } = useQuery(
		['paralogs', payload],
		() => fetchData(payload, '/target-assessment/paralogs/'),
		{
			enabled: !!target,
		}
	);

	const speciesList = useMemo(() => {
		if (!paralogsData?.paralogs) return [];
		return Object.keys(paralogsData.paralogs).filter(species => 
			paralogsData.paralogs[species].length > 0
		);
	}, [paralogsData]);

	const speciesConfig = useMemo(() => {
		const config = {};
		const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'];
		speciesList.forEach((species, index) => {
			config[species.toLowerCase()] = {
				color: colors[index % colors.length],
				xPos: index + 1
			};
		});
		return config;
	}, [speciesList]);

	const allSpeciesData = useMemo(() => {
		if (!paralogsData?.paralogs) return [];
		const all = Object.values(paralogsData.paralogs).flat();
		return all;
	}, [paralogsData]);

	const processedData = useMemo(() => {
		if (!allSpeciesData.length || !Object.keys(speciesConfig).length) return [];
	
		return allSpeciesData.map((item: any) => {
			const species = item.Species?.toLowerCase().trim();
			const identityScore = Number(item["Identity Score"]) || 0;
			const xPos = speciesConfig[species]?.xPos || 0;
	
			const speciesData: SpeciesDataItem[] = allSpeciesData.filter(
				(d: any) => d.Species?.toLowerCase() === species
			) as SpeciesDataItem[];
	
			const avgScore = speciesData.length > 0
    ? speciesData.reduce<number>(
        (sum, d) => sum + (Number(d["Identity Score"]) || 0),
        0
    ) / speciesData.length
    : 0;
	
			return {
				...item,
				x: xPos + (Math.random() - 0.5) * 0.3,
				identityScore,
				cluster: identityScore > avgScore ? "High" : "Low",
				color: speciesConfig[species]?.color || "#000000",
			};
		});
	}, [allSpeciesData, speciesConfig]);

	const CustomTooltip = ({ active, payload }) => {
		if (active && payload && payload.length) {
			const data = payload[0].payload;
			return (
				<div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
					<p className="font-semibold text-gray-800 capitalize">{data.Species}</p>
					<p className="text-sm text-blue-600 font-medium">Gene: {data["Gene2 Symbol"].toUpperCase()}</p>
					<p className="text-sm text-gray-600">
						Identity Score: {data.identityScore.toFixed(3)}
					</p>
				</div>
			);
		}
		return null;
	};

	const ClusterShape = (props) => {
		const { cx, cy, fill, payload } = props;
		const size = showClusters ? (payload.cluster === 'High' ? 8 : 6) : 6;
		const strokeWidth = showClusters ? (payload.cluster === 'High' ? 2 : 1) : 0;
		
		return (
			<circle 
				cx={cx} 
				cy={cy} 
				r={size} 
				fill={fill} 
				fillOpacity={0.6}
				stroke={showClusters ? fill : 'none'}
				strokeWidth={strokeWidth}
			/>
		);
	};

	const rowData = useMemo(() => {
		const data = [];
	  
		if (paralogsData && paralogsData.paralogs) {
		  for (const key in paralogsData.paralogs) {
			const elements = paralogsData.paralogs[key];
	  
			// Skip invalid or error entries
			if (!elements || elements.error) continue;
	  
			// Ensure elements is an array
			if (Array.isArray(elements)) {
			  data.push(...elements);
			} else {
			  console.warn(`Unexpected data format for ${key}:`, elements);
			}
		  }
		}
	  
		return data;
	  }, [paralogsData]);

	const defs = useMemo(() => {
		if (rowData.length === 0) return [];
		
		return Object.keys(rowData[0]).map((key) => {
			const def: any = { field: key };

			if (key === 'Paralog Pair URL') {
				def.cellRenderer = (params: any) =>
					params.value ? (
						<a target='_blank' href={params.value} rel='noreferrer'>
							expression data
						</a>
					) : null;
			}

			if (key === 'Common GO slim') {
				def.minWidth = 540;
			}
			if (key === 'Paralog Score') {
				def.headerComponent = CustomHeader;
				def.headerComponentParams = {
					displayName: "Paralog Score",
					title: "The score presents the number of independent orthology/paralogy prediction algorithms that support a paralogous relationship for a given gene pair within a species. Higher the score, higher is the consensus."
				};
				def.minWidth = 170;
			}
			if (key === "DIOPT Score") {
				def.headerComponent = CustomHeader;
				def.headerComponentParams = {
					displayName: "DIOPT Score",
					title: "Reflects the agreement of the paralog/ortholog prediction among various algorithms. A score of 2 means at least two algorithms support the paralogy. Higher the score, higher is the consensus."
				};
			}

			return def;
		});
	}, [rowData]);

	const xTicks = speciesList.map((_, index) => index + 1);
	const xDomain = [0.5, speciesList.length + 0.5];

	return (
		<section id='paralogs' className='mt-12'>
			<h1 className='text-3xl font-semibold'>Paralogs</h1>
			<p className='mt-2 font-medium'>
			The sections provides homologs and paralogs for {target} across selected species (Human, mouse, fly, zebrafish & worm) which helps anticipate potential off-target interactions and improve drug specificity. Higher the identity score, greater are the chances for off-target effects.
			</p>
			<div className='flex justify-end mb-4'>
				<div className="flex border border-gray-200 rounded-lg bg-white">
					<ConfigProvider
						theme={{
							components: {
								Segmented: {
									itemSelectedBg: "#1677ff",
									itemSelectedColor: "white",
								},
							},
						}}
					>
						<Segmented
							options={[
								{
									label: "",
									value: "list",
									icon: <List />,
								},
								{
									label: "",
									value: "grid",
									icon: <ChartLine className="w-5 h-5 mt-1"/>,
								},
							]}
							value={viewMode}
							onChange={(value) => setViewMode(value as "grid" | "list")}
						/>
					</ConfigProvider>
				</div>
			</div>
			{paralogsError ? (
				<div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
					<Empty />
				</div>
			) : (
				<>
					{viewMode === "list" && (
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
					{viewMode === "grid" && processedData.length > 0 && (
						<ResponsiveContainer width="100%" height={500}>
							<ScatterChart margin={{ top: 20, right: 30, bottom: 60, left: 60 }}>
								<CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
								<XAxis
									type="number"
									dataKey="x"
									domain={xDomain}
									ticks={xTicks}
									tickFormatter={(value) => {
										const species = speciesList[value - 1];
										return species ? species.charAt(0).toUpperCase() + species.slice(1) : '';
									}}
									label={{
										value: 'Species',
										position: 'insideBottom',
										offset: -12,
										style: { fontSize: 14, fontWeight: 600 },
									}}
								/>
								<YAxis
									type="number"
									dataKey="identityScore"
									name="Identity Score"
									domain={[0, 1]}
									label={{
										value: 'Identity Score',
										angle: -90,
										position: 'insideLeft',
										style: { fontSize: 14, fontWeight: 600 },
									}}
								/>
								<Tooltip content={<CustomTooltip active={undefined} payload={undefined} />} />
								<Legend iconType="circle" verticalAlign="bottom" wrapperStyle={{ paddingTop: '20px', marginLeft:"30px" }} />

								{Object.keys(speciesConfig).map((species) => {
									const speciesData = processedData.filter(
										(d: any) => d.Species?.toLowerCase() === species
									);
									return (
										<Scatter
											key={species}
											name={species.charAt(0).toUpperCase() + species.slice(1)}
											data={speciesData}
											fill={speciesConfig[species].color}
											shape={(props) => <ClusterShape {...props} />}
										/>
									);
								})}
							</ScatterChart>
						</ResponsiveContainer>
					)}
					{
						viewMode === "grid" && processedData.length === 0 && (
							<div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
								<Empty description="No data available" />
							</div>
						)
					}
				</>
			)}
		</section>
	);
};

export default Paralogs;