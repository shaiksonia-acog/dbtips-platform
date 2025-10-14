// import Plot from 'react-plotly.js';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import LoadingButton from '../../components/loading';
import { Empty } from 'antd';
import { useMemo, useState } from 'react';
// import json from '../../assets/ADORA3.json';

// const response = json.target_prioritisation.targetability;
const metricInfo = {
    "Target in clinic": "0: Pre-clinical/Research | 0.25: Phase I | 0.5: Phase II | 0.75: Phase III | 1: Phase IV",
    "Membrane protein": "1 = Protein target is located (at least) in the cell or plasma membrane. 0 = Protein target is not located in the cell membrane but some location information is accessible.",
    "Secreted protein": "1 = Protein target is (at least) secreted or predicted to be secreted. 0 = Not secreted but with location information.",
    "Ligand binder": "1 = Target has a high-quality ligand reported. 0 = Target does not have high-quality ligand reported.",
    "Small molecule binder": "1 = Target has a small molecule reported. 0 = Target does not have a small molecule reported.",
    "Predicted pockets": "1 = Target contains a high-quality predicted pocket. 0 = Target does not have a high-quality predicted pocket.",
    "Mouse ortholog identity": "1 = There is at least one gene in mice that contains a sequence with a 100% of identity with the target. 0 = There are no genes in mice containing a sequence with at least 80% of identity with the target.",
    "Chemical probes": "1 = Target has high-quality chemical probes. 0 = Target does not have high-quality chemical probes.",
    "Genetic constraint": "A score from -1 to 1 is given to genes depending on their LOEUF metric rank, being -1 the least tolerant to LoF variation and 1 the most tolerant.",
    "Mouse models": "> 0 = When the target has been knocked-out in mice there were multiple and severe phenotypes reported, with a score higher than the first quartile. 0 = Either the target has non-severe phenotypes reported or is in the first quartile of the normalised score.",
    "Gene essentiality": "-1 = Target reported as essential. 0 = Target not reported as essential.",
    "Known safety events": "-1 = The target has at least one adverse event.",
    "Cancer driver gene": "-1 = Target is catalogued as driver gene (tumour suppressor, oncogene or both).",
    "Paralogues": ">0 are linearly scored those targets with at least one paralogue in human harbouring at least 60% of identity with the target. 0 = Those targets with paralogues harbouring less than 60% of identity.",
    "Tissue specificity": "-1: Low tissue specificity | -0.5: Tissue enhanced ≥4 fold higher mRNA level in a given tissue compared to average of all other tissues | 0.75: Group enriched ≥4 fold higher average mRNA in 2-5 tissue compared to any other | 1: Tissue enriched ≥4 fold higher mRNA in a given tissue compared to any other.",
    "Tissue distribution": "-1: Detected in all | 0: Detected in many (at least 1/3 but not all tissues) | 0.5: Detected in some (more than one but less than 1/3 of tissues) | 1: Detected in single tissue"
  };
  const formatValue = (value) => {
    if (value === "no data") return "N/A";
    return typeof value === 'number' ? value.toFixed(2) : value;
  };
  const getColor = (value) => {
	if (value === "no data") return "#e0e0e0";
    
    // Normalize value from [-1, 1] to [0, 1]
    const normalized = (value + 1) / 2;
    
    // Create smooth gradient from red (-1) through yellow (0) to green (1)
    let r, g, b;
    
    if (normalized < 0.5) {
      // Red to Yellow (0 to 0.5 normalized, or -1 to 0 actual)
      const t = normalized * 2; // 0 to 1
      r = 217; // Red component stays high
      g = Math.round(83 + (240 - 83) * t); // Green increases
      b = Math.round(79 + (173 - 79) * t); // Blue increases slightly
    } else {
      // Yellow to Green (0.5 to 1 normalized, or 0 to 1 actual)
      const t = (normalized - 0.5) * 2; // 0 to 1
      r = Math.round(240 - (240 - 30) * t); // Red decreases
      g = Math.round(240 - (240 - 123) * t); // Green decreases slightly
      b = Math.round(173 - (173 - 52) * t); // Blue decreases
    }
    
    return `rgb(${r}, ${g}, ${b})`;
  };

 
  const cellWidth = 78;
  const cellHeight = 60;
  const yAxisWidth = 120;
  const xAxisHeight = 150;
const Targetability = ({ target,  }) => {
	const [hoveredMetric, setHoveredMetric] = useState(null);

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
	// const customHoverText = allValues.map((value, index) => {
	// 	const feature = allKeys[index];
	// 	const target = targetabilityData?.targetability?.['Approved Symbol'];
		
	// 	if (value === null) {
	// 		return `<b>${feature}</b><br>Target: ${target}<br>Status: No evidence available`;
	// 	} else if (value > 0) {
	// 		return `<b>${feature}</b><br>Target: ${target}<br>Score: ${value.toFixed(2)}<br>Assessment: Favourable`;
	// 	} else if (value < 0) {
	// 		return `<b>${feature}</b><br>Target: ${target}<br>Score: ${value.toFixed(2)}<br>Assessment: Unfavourable`;
	// 	} else {
	// 		return `<b>${feature}</b><br>Target: ${target}<br>Score: ${value}<br>Assessment: Neutral`;
	// 	}
	// });
	// const metric = Object.keys(targetabilityData.targetability.Prioritisation);
const metrics = useMemo(() => {
	if (targetabilityData) {
	  return Object.keys(targetabilityData.targetability.Prioritisation);
	}
	return [];
  }, [targetabilityData]);
	return (
		<section id='targetability' className='mt-12 px-[5vw]'>
			<h1 className='text-3xl font-semibold'>Targetability</h1>
			<p className='italic font-medium mt-2'>
		 The section presents target-specific properties in a disease-agnostic manner. Using a color scale, it helps users quickly assess targets for prioritization or deprioritization.
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
					<div className="  ">
          <div className="relative overflow-x-auto">
            <div className="inline-block" style={{ minWidth: `${metrics.length * cellWidth + yAxisWidth}px`, paddingTop: `${xAxisHeight}px` }}>
              
              {/* X-axis labels */}
              <div className="absolute top-0" style={{ height: `${xAxisHeight}px`, left: `${yAxisWidth + 25}px` }}>
                <div className="flex gap-1">
                  {metrics.map((metric, idx) => (
                    <div
                      key={idx}
                      className="relative flex items-end justify-start"
                      style={{ width: `${cellWidth}px`, height: `${xAxisHeight - 10}px` }}
                    >
                      <div 
                        className="text-base text-gray-700 font-medium whitespace-nowrap"
                        style={{ 
                          transform: 'rotate(-50deg)',
                          transformOrigin: 'left bottom',
                          marginBottom: '2px'
                        }}
                      >
                        {metric}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Y-axis label and heatmap row */}
              <div className="flex items-center">
                {/* Y-axis label */}
                <div 
                  className="flex-shrink-0 bg-gray-100 px-4 py-3 rounded font-semibold text-gray-700 border border-gray-300 text-center"
                  style={{ width: `${yAxisWidth}px`, height: `${cellHeight}px` }}
                >
                  {targetabilityData.targetability["Approved Symbol"].toUpperCase()}
                </div>
                
                {/* Heatmap cells */}
                <div className="flex gap-1 ml-2">
                  {metrics.map((metric, idx) => {
                    const value = targetabilityData.targetability.Prioritisation[metric];
                    return (
                      <div
                        key={idx}
                        className="relative w-[78px]"
                        // style={{ width: `${cellWidth}px` }}
                        onMouseEnter={() => setHoveredMetric(metric)}
                        onMouseLeave={() => setHoveredMetric(null)}
                      >
                        <div
                          className="rounded cursor-pointer transition-all duration-200 flex items-center justify-center font-semibold text-sm border-2 border-transparent hover:border-blue-500 hover:shadow-lg"
                          style={{ 
                            backgroundColor: getColor(value),
                            height: `${cellHeight}px`
                          }}
                        >
                          <span className={value === "no data" ? "text-gray-600" : "text-white"}>
                            {formatValue(value)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </div>
		<div className='flex justify-center items-center'>
			<p className='mt-4 font-bold text-gray-600'>
			Target Prioritisation Features
			</p>
		</div>
        {/* Info box */}
        {hoveredMetric && (
          <div className="mt-6 bg-blue-50 border-l-4 border-blue-500 p-4 rounded shadow-md">
            <h3 className="font-bold text-blue-900 mb-2">{hoveredMetric}</h3>
            <p className="text-gray-700 text-sm leading-relaxed">{metricInfo[hoveredMetric]}</p>
            <p className="text-blue-800 font-semibold mt-2">
              Value: {formatValue(targetabilityData.targetability.Prioritisation[hoveredMetric])}
            </p>
          </div>
        )}

        {/* Legend */}
        {/* <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h3 className="font-bold text-gray-800 mb-4">Score Legend</h3>
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "#d9534f" }}></div>
              <span className="text-sm text-gray-700">-1.0 to -0.6</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "#e67e22" }}></div>
              <span className="text-sm text-gray-700">-0.6 to -0.3</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "#f0ad4e" }}></div>
              <span className="text-sm text-gray-700">-0.3 to 0.0</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "#5cb85c" }}></div>
              <span className="text-sm text-gray-700">0.0 to 0.5</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded" style={{ backgroundColor: "#1e7b34" }}></div>
              <span className="text-sm text-gray-700">0.5 to 1.0</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded bg-gray-300"></div>
              <span className="text-sm text-gray-700">No data</span>
            </div>
          </div>
        </div> */}

					
				</div>
			)}
		</section>
	);
};

export default Targetability;
