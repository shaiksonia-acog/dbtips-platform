import { useState, useEffect, useMemo, useCallback } from 'react';
import { useQuery } from 'react-query';
import { Select, Pagination, Empty, Button } from 'antd';
import LoadingButton from '../../components/loading';
import { fetchData } from '../../utils/fetchData';
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../../utils/parseUrlParams';
import Card from './card';
import { useChatStore } from 'chatbot-component';
import BotIcon from '../../assets/bot.svg?react';
import { preprocessRnaseqData } from '../../utils/llmUtils';

import ExportButton from '../../components/exportButton';
import { convertToArray } from '../../utils/helper';
const { Option } = Select;
// Move constants outside component to prevent recreation
const PAGE_SIZE = 5;

const RnaSeqCard = () => {

	const [uniquePlatformNames, setUniquePlatformNames] = useState([]);
	const location = useLocation();
	const [indications, setIndications] = useState([]);
	const [dataArray, setDataArray] = useState([]);
	const [filters, setFilters] = useState({
		disease: indications,
		organism: 'All',
		page: 1,
		studyType: 'All',
		platformName: 'All',
		sampleType: 'All', // Added new filter for sampleType
		GSEId:[]
	});
	const { register, invoke } = useChatStore();

	const queryPayload = useMemo(
		() => ({
			diseases: indications,
		}),
		[indications]
	);

	useEffect(() => {
		const queryParams = new URLSearchParams(location.search);
		const { indications: newIndications, diseaseArea } = parseQueryParams(queryParams);
		setIndications(newIndications.length > 0 ? indications : diseaseArea);
	}, [location]);

	const {
		data: rnaSeqData,
		error,
		isLoading,
	} = useQuery(
		['rnaSeqData', queryPayload],
		() => fetchData(queryPayload, '/evidence/rna-sequence/'),
		{
			enabled: Boolean(indications.length),
			refetchOnWindowFocus: false,
			staleTime: 1000 * 60 * 5, // 5 minutes in milliseconds
			refetchOnMount: false,
		}
	);
	useEffect(() => {
		setFilters((prev) => ({
			...prev,
			disease: indications,
		}));
	}, [indications]);
	useEffect(() => {
		if (!rnaSeqData) return;
		const updatedData = convertToArray(rnaSeqData);
		setDataArray(updatedData);
	}, [rnaSeqData]);

	useEffect(() => {
		if (dataArray.length === 0) return;
		const uniquePlatformNames =
			dataArray.length > 0
				? Array.from(
					new Set(
						(filters.disease.includes('All') // Check if "All" is selected
							? dataArray
							: dataArray.filter((data) =>
								filters.disease.some(
									(disease) => disease.toLowerCase() === data.Disease.toLowerCase()
								)
							)
						).flatMap((data) => data.PlatformNames) // Flatten arrays of PlatformNames
					)
				)
				: [];


		setUniquePlatformNames(uniquePlatformNames);
	}, [dataArray, filters, rnaSeqData]);

	const {
		filteredData,
		paginatedData,
		totalItems,
		totalStudies,
		singleRnaCount,
		bulkRnaCount,
		MicroarrayCount,
		bulkRnaCountInHuman,
		singleRnaCountInHuman,
		microarrayCountInHuman,
		diseasedSampleCount,
		bothSampleCount,
		unknownSampleCount,
	} = useMemo(() => {
		const availableDiseases = Object.keys(rnaSeqData || {});
		const selectedDiseaseData =
			filters.disease.includes('All')
				? dataArray
				: dataArray.filter((data) =>
					filters.disease.some(
						(disease) => disease.toLowerCase() === data.Disease.toLowerCase()
					)
				)

		const filtered = selectedDiseaseData.filter((data) => {
			// Check if the organism filter is "All" or matches the organism
			const organismMatches =
				filters.organism === 'All' || data.Organism[0] === filters.organism;
			const platformNameMatches =
				filters.platformName === 'All' ||
				data.PlatformNames.includes(filters.platformName);
			// Check if the study type matches the selected filter
			const studyTypeMatches =
				filters.studyType === 'All' || data.StudyType == filters.studyType;
			// Check if the sample type matches the selected filter
			const sampleTypeMatches =
				filters.sampleType === 'All' || data.SampleType === filters.sampleType;
			const GSEIdMatches =
				filters.GSEId.length==0 || 
				(Array.isArray(filters.GSEId) 
					? filters.GSEId.includes(data.GseID)
					: data.GseID === filters.GSEId);

			// Include data only if it matches all filters
			return organismMatches && studyTypeMatches && platformNameMatches && sampleTypeMatches&&GSEIdMatches;
		});

		const totalStudies = selectedDiseaseData.length;
		// Count human studies in the selectedDiseaseData
		const humanStudiesCount = selectedDiseaseData.filter(
			(data) => data.Organism?.[0] === 'Human'
		).length;
		const singleRnaCount = selectedDiseaseData.filter(
			(data) => data.StudyType === 'scRNA'
		).length;
		const bulkRnaCount = selectedDiseaseData.filter(
			(data) => data.StudyType === 'bulkRNA'
		).length;
		const bulkRnaCountInHuman = selectedDiseaseData.filter(
			(data) => data.StudyType === 'bulkRNA' && data.Organism?.[0] === 'Human'
		).length;

		const singleRnaCountInHuman = selectedDiseaseData.filter(
			(data) => data.StudyType === 'scRNA' && data.Organism?.[0] === 'Human'
		).length;

		const MicroarrayCount = selectedDiseaseData.filter(
			(data) => data.StudyType === 'Microarray'
		).length;
		const microarrayCountInHuman = selectedDiseaseData.filter(
			(data) => data.StudyType === 'Microarray' && data.Organism?.[0] === 'Human'
		).length;

		// Add counts for sample types
		const controlSampleCount = selectedDiseaseData.filter(
			(data) => data.SampleType === 'Control'
		).length;

		const diseasedSampleCount = selectedDiseaseData.filter(
			(data) => data.SampleType === 'Diseased'
		).length;

		const bothSampleCount = selectedDiseaseData.filter(
			(data) => data.SampleType === 'Both'
		).length;

		const unknownSampleCount = selectedDiseaseData.filter(
			(data) => data.SampleType === 'Unknown' || !data.SampleType
		).length;

		return {
			diseases: availableDiseases,
			filteredData: filtered,
			paginatedData: filtered.slice(
				(filters.page - 1) * PAGE_SIZE,
				filters.page * PAGE_SIZE
			),
			totalItems: filtered.length,
			totalStudies,
			humanStudiesCount,
			singleRnaCount,
			bulkRnaCount,
			MicroarrayCount,
			bulkRnaCountInHuman,
			singleRnaCountInHuman,
			microarrayCountInHuman,
			controlSampleCount,
			diseasedSampleCount,
			bothSampleCount,
			unknownSampleCount
		};
	}, [rnaSeqData, filters, dataArray]);
	const handleFilterChange = useCallback((key, value) => {
		if (key === 'disease') {
			if (value.includes('All')) {
				setFilters((prev) => ({
					...prev,
					[key]: indications,
					page: 1,
				}));
			}
			else if (filters.disease.length === indications.length && value.length < indications.length) {
				setFilters((prev) => ({
					...prev,
					[key]: value,
					page: 1,
				}));
			}
			else {
				setFilters((prev) => ({
					...prev,
					[key]: value,
					page: 1,
				}));
			}
		}
		else {
			setFilters((prev) => ({
				...prev,
				[key]: value,
				page: key !== 'page' ? 1 : value,
			}));
		}

	}, []);

	useEffect(() => {
		if (filteredData && filters?.disease) {
			const llmData = preprocessRnaseqData(filteredData);
			register('rnaseq', {
				disease:
					filters.disease.includes('All')
						? indications.map((indication) => indication.toLowerCase())
						: filters.disease,
				organism: filters.organism,
				platform_name: filters.platformName,
				study_type:
					filters.studyType == 'All'
						? ['scRNA', 'bulkRNA', 'Microarray', 'Not Known']
						: filters.studyType,
				sample_type:
					filters.sampleType == 'All'
						? ['Diseased', 'Both', 'Unknown'] // Control option removed
						: filters.sampleType,
				data: llmData,
			});
		}
	}, [filteredData, filters]);

	const handleLLMCall = () => {
		invoke('rnaseq', { send: false });
	};

	return (
		<article id='rnaSeq'>
			<div className='flex space-x-5 items-center'>
				<h1 className='text-3xl font-semibold'>RNA-seq Datasets</h1>
				<Button
					type='default' // This will give it a simple outline
					onClick={handleLLMCall}
					className='w-18 h-8 text-blue-800 text-sm flex items-center'
				>
					<BotIcon width={16} height={16} fill='#d50f67' />
					<span>Ask LLM</span>
				</Button>
			</div>
			<p className=' font-medium mt-2 mb-2'>
				Single-cell studies provide more granular insights compared to bulk
				studies.
			</p>
			{isLoading && <LoadingButton />}
			{error && !rnaSeqData && <Empty description={`${error}`} />}
			{/* {!isLoading && !error  && !rnaSeqData && (
        <Empty description="No data available" />
      )} */}
			{filters.disease && !isLoading && dataArray.length > 0 && (
				<section className='mb-10'>
					<div className='flex justify-between my-2'>
						<div className='flex flex-wrap gap-2'>
							<div>
								<span>Disease: </span>
								<Select
									placeholder='Select indications'
									value={filters.disease}
									onChange={(value) => handleFilterChange('disease', value)}
									style={{ width: 300 }}
									maxTagCount='responsive'
									mode='multiple'
								>
									<Option key='all' value='All'>
										All
									</Option>
									{indications.map((disease) => (
										<Option key={disease} value={disease}>
											{disease}
										</Option>
									))}
								</Select>
							</div>

							<div>
								<span>Organism: </span>
								<Select
									className='w-32'
									placeholder='Select an organism'
									value={filters.organism}
									onChange={(value) => handleFilterChange('organism', value)}
								>
									<Option value='Human'>Human</Option>
									<Option value='All'>All</Option>
								</Select>
							</div>
							<div>
								<span>Platform name: </span>
								{uniquePlatformNames && dataArray && (
									<Select
										style={{ width: 200 }}
										placeholder='Select a platform'
										value={filters.platformName}
										showSearch
										onChange={(value) =>
											handleFilterChange('platformName', value)
										}
									>
										<Option key='all' value='All'>
											All
										</Option>

										{uniquePlatformNames.map((platformName) => (
											<Option key={platformName} value={platformName}>
												{platformName}
											</Option>
										))}
									</Select>
								)}
							</div>
							<div>
								<span>Study type: </span>
								<Select
									style={{ width: 150 }}
									placeholder='Select a Study Type'
									value={filters.studyType}
									onChange={(value) => handleFilterChange('studyType', value)}
								>
									<Option value='All'>All</Option>
									<Option value='scRNA'>scRNA</Option>
									<Option value='bulkRNA'>bulkRNA</Option>
									<Option value='Microarray'>Microarray</Option>
									<Option value='Not Known'>Not Known</Option>
								</Select>
							</div>
							<div>
								<span>Sample type: </span>
								<Select
									style={{ width: 150 }}
									placeholder='Select a Sample Type'
									value={filters.sampleType}
									onChange={(value) => handleFilterChange('sampleType', value)}
								>
									<Option value='All'>All</Option>
									{/* Control option removed */}
									<Option value='Diseased'>Diseased</Option>
									<Option value='Both'>Both</Option>
									<Option value='Unknown'>Unknown</Option>
								</Select>
							</div>
							<div>
								<span>Filter by study ID: </span>
								<Select
									style={{ width: 300 }}
									placeholder='Select GEO accession'
									value={filters.GSEId}
									onChange={(value) => handleFilterChange('GSEId', value)}
									allowClear
									showSearch
									
									mode='multiple'
								>
									{/* Control option removed */}
									{dataArray
										.map((data) => data.GseID)
										.sort()
										.map((gseId) => (
											<Option key={gseId} value={gseId}>{gseId}</Option>
										))}
								</Select>
							</div>
						</div>
						{
							<ExportButton
								indications={indications}
								endpoint={'/evidence/rna-sequence/'}
								fileName={'RNASeqDataset'}
							/>
						}
					</div>
					<span className='font-bold'>Summary: </span>
					<span>
						{' '}
						<span className='text-sky-800'>{totalStudies} </span>studies for selected disease:{' '}
						<span className='text-sky-800'>{bulkRnaCount}</span> bulk-RNA {' ( '}
						<span className='text-sky-800'>{bulkRnaCountInHuman}</span> for Human {' ), '}
						<span className='text-sky-800'>{singleRnaCount}</span> sc-RNA {' ( '}
						<span className='text-sky-800'>{singleRnaCountInHuman}</span> for Human {' ), '}
						<span className='text-sky-800'>{MicroarrayCount}</span> microarrays {' ( '}
						<span className='text-sky-800'>{microarrayCountInHuman}</span> for Human {' ) '}
					</span>
					<div className='mt-2'>
						<span className='font-bold'>Sample Types: </span>
						<span>
							<span className='text-sky-800'>{diseasedSampleCount}</span> Diseased, {' '}
							<span className='text-sky-800'>{bothSampleCount}</span> Both (Control+Diseased), {' '}
							<span className='text-sky-800'>{unknownSampleCount}</span> Unknown
						</span>
					</div>
					<div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px' }}>
						{paginatedData.map((diseaseData, index) => (
							<Card
								key={`${filters.disease}-${index}-${filters.page}`}
								diseaseData={diseaseData}
							/>
						))}
					</div>
					{paginatedData.length == 0 && (
						<div className='flex items-center justify-center h-[50vh]'>
							<Empty description='No data available' />
						</div>
					)}

					{totalItems > PAGE_SIZE && (
						<Pagination
							current={filters.page}
							pageSize={PAGE_SIZE}
							total={totalItems}
							onChange={(page) => handleFilterChange('page', page)}
							showSizeChanger={false}
							className='mt-5'
						/>
					)}
				</section>
			)}
			{
				!isLoading && !error && rnaSeqData && filteredData.length === 0 &&
				<div className='h-[50vh] flex justify-center items-center'>
					<Empty description="No data available" />
				</div>
			}

		</article>
	);
};

export default RnaSeqCard;