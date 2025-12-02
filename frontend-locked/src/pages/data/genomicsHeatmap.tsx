import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useQuery } from 'react-query';
import { fetchData } from '../../utils/fetchData';
import { Empty } from 'antd';
import LoadingButton from '../../components/loading';

const categoryColors = {
  'ECG Traits': '#E63946',          
  'CARDIOVASCULAR': '#1D3557',      
  'HEMATOLOGICAL': '#457B9D',       
  'Anthropometric': '#9B59B6',      // Changed from brown to purple
  'Sleep And Circadian': '#F4A261', 
  'HEPATIC': '#E9C46A',             
  'LIPIDS': 'blue',                 
  'GLYCEMIC': 'green',              
  'RENAL': '#00B4D8',               
  'METABOLITE': '#FF006E',          
  'ATRIAL FIBRILLATION': '#8338EC', 
  'Musculoskeletal': '#16A085',     // Changed from red (#8B0000) to teal
  'Ocular': '#008080',
  'Other': '#708090',
  'Diabetic Complications': '#FF8C00',
  'Type 1 Diabetes': '#2E8B57',
  'Aging and Longevity': '#6A5ACD',
};

const generateColorscale = () => {
  const colors = [
    '#FFF8F8', '#FFE5E5', '#FFCCCC', '#FFB3B3', '#FF9999',
    '#FF8080', '#FF6666', '#FF4D4D', '#FF3333', '#FF1A1A',
    '#E60000', '#CC0000', '#B30000', '#990000', '#800000'
  ];
  
  return colors.map((color, index) => {
    const position = index / (colors.length - 1);
    return [position, color];
  });
};

const HeatmapComponent = ({ target }) => {
  const heatmapRef = useRef(null);
  const [error, setError] = useState(null);

  const payload = { target };

  const {
    data: heatmapData,
    isLoading,
    isError,
    error: fetchError,
  } = useQuery(
    ['evidence-heatmap', payload],
    () => fetchData(payload, '/genomics/evidence-heatmap/'),
    {
      enabled: !!target,
      staleTime: 5 * 60 * 1000,
      cacheTime: 30 * 60 * 1000,
    }
  );

  useEffect(() => {
    if (!heatmapData || !heatmapRef.current) return;

    const renderHeatmap = () => {
      try {
        const dataJson = heatmapData;
        const unsortedTraitData = dataJson[Object.keys(dataJson)[0]];
     
        if (!unsortedTraitData || unsortedTraitData.length === 0) {
          setError('No data available');
          return;
        }

        // Sort by category
        const traitData = [...unsortedTraitData].sort((a, b) =>
          a.category.localeCompare(b.category)
        );

        const traits = traitData.map((item) => item?.trait?.trim());
        const categories = traitData.map((item) => item.category);
        const evidenceTypes = Object.keys(traitData[0].evidenceCounts);

        const data = evidenceTypes.map((evidenceType) =>
          traitData.map((item) => item.evidenceCounts[evidenceType]['score'])
        );
       
        const reversedData = data.reverse();
        const reversedEvidenceTypes = [...evidenceTypes].reverse();
        const displayEvidenceTypes = reversedEvidenceTypes.map(type => {
          if (type.toLowerCase() === 'phewas') return 'PheWAS';
        
          if (type.toUpperCase() === 'COLOC') return 'Colocalisation';
          return type;
        });
      
     
        const hoverText = reversedEvidenceTypes.map((evidenceType, rowIndex) =>
          traitData.map((item) => {
            const evidence = item.evidenceCounts[evidenceType]; 
            let hoverInfo = `<b>${item.trait}</b><br>Evidence: ${displayEvidenceTypes[rowIndex]}<br>Score: ${evidence.score}`;  
        
            if (evidenceType.toLowerCase() === 'fine mapping') {
              if (evidence['Mean PP'] !== null && evidence['Mean PP'] !== undefined) {
                hoverInfo += `<br>Mean PP: ${evidence['Mean PP'].toFixed(4)}`;
              }
            } else if (evidenceType.toUpperCase() === 'COLOC') {
              if (evidence.pp_h4_abf !== null && evidence.pp_h4_abf !== undefined) {
                hoverInfo += `<br>pp_h4_abf: ${evidence.pp_h4_abf.toFixed(4)}`;
              }
            } 
            else if (evidenceType.toLowerCase() === 'phewas') {
              if (evidence.huge_score !== null && evidence.huge_score !== undefined) {
                hoverInfo += `<br>HuGE score: ${evidence.huge_score}`;
              }}
            else if (evidenceType.toLowerCase() !== 'total') {
              if (evidence.pval !== null && evidence.pval !== undefined) {
                hoverInfo += `<br>p-value: ${evidence.pval.toExponential(2)}`;
              }
            }
        
            return hoverInfo;
          })
        );

        // Main heatmap trace
        const heatmapTrace = {
          z: reversedData,
          x: traits,
          y: displayEvidenceTypes,  // Use display names here
          type: 'heatmap',

          colorscale:generateColorscale(),
          showscale: true,
          hoverongaps: false,
          text: hoverText,
          hovertemplate: '%{text}<extra></extra>',
          colorbar: {
            thickness: 15,
            // len: 0.7,
            x: 1,
            tickfont: { size: 10 },

          },
          xaxis: 'x',
          yaxis: 'y'
        };

        // FIXED: Category color strip - build proper discrete colorscale
        const categoryColorScale = [];
        traits?.forEach((_trait, i) => {
          const start = i / traits.length;
          const end = (i + 1) / traits.length;
          
          // Get color with case-insensitive fallback
          const categoryKey = Object.keys(categoryColors).find(
            key => key.toLowerCase() === categories[i].toLowerCase()
          );
          const color = categoryColors[categories[i]] || categoryColors[categoryKey] || '#95A5A6';
          
          categoryColorScale.push([start, color]);
          if (i < traits.length - 1) {
            categoryColorScale.push([end - 0.0001, color]);
          } else {
            categoryColorScale.push([1, color]);
          }
        });

        const categoryTrace = {
          z: [traits.map((_, i) => i)],
          x: traits,
          y: ['Categories'],
          type: 'heatmap',
          colorscale: categoryColorScale,
          showscale: false,
          customdata: [categories],
          hovertemplate: '<b>%{x}</b><br>Category: %{customdata}<extra></extra>',
          xaxis: 'x2',
          yaxis: 'y2',
          xgap: 1,
          ygap: 0
        };

        // Layout
        const layout = {
          grid: {
            rows: 2,
            columns: 1,
            pattern: 'independent',
            roworder: 'top to bottom',
            subplots: [['xy'], ['x2y2']]
          },
          xaxis: { 
            showticklabels: false,
            domain: [0, 1],      // ADD THIS
    anchor: 'y'  ,
          },
          yaxis: {
          title: { text: 'Evidence types', font: { size: 12,weight: 'bold' }, standoff: 10 },
          tickfont: { size: 11,weight: 'bold' },
          automargin: true,
          domain: [0.00, 1],
          anchor: 'x'          

          },
          xaxis2: {
          tickangle: -45,
          title: { text: 'Traits', font: { size: 12,weight: 'bold'}, standoff: 10 },
          side: 'bottom',
          tickfont: { size: 9,weight: 'bold' },
          showticklabels: true,
          domain: [0, 1],
          automargin: true,
          anchor: 'y2',        
      matches: 'x'  ,
      tickvals: traits.map((_, i) => i),    
      ticktext: traits,
       
          },
          yaxis2: {
          tickfont: { size: 11, weight: 'bold' },
          automargin: true,
          domain: [0, 0.04],
          anchor: 'x2'         // ADD THIS

          },
          margin: { l: 100, r: 120, t: 20, b: 200 },
          paper_bgcolor: 'white',
          plot_bgcolor: 'white',
        };

        const config = {
          responsive: true,
          displayModeBar: true,
          // modeBarButtonsToRemove: ['lasso2d', 'select2d'],
          displaylogo: false,
          modeBarStyle: {
            top: "5px",
            right: "2px"  
          }
        };

        Plotly.newPlot(heatmapRef.current, [heatmapTrace, categoryTrace], layout, config);
      } catch (err) {
        console.error('Heatmap render error:', err);
        setError(err.message);
      }
    };

    renderHeatmap();

    return () => {
      if (heatmapRef.current) {
        Plotly.purge(heatmapRef.current);
      }
    };
  }, [heatmapData]);

  // Category legend
  const [uniqueCategories, setUniqueCategories] = useState([]);

  useEffect(() => {
    if (heatmapData) {
      const dataKey = Object.keys(heatmapData)[0];
      const categories = heatmapData[dataKey]
        ? [...new Set(heatmapData[dataKey].map((item) => item.category))]
        : [];
      setUniqueCategories(categories);
    }
  }, [heatmapData]);

  if (isLoading) {
    return <LoadingButton />;
  }

  if (isError || error || fetchError) {
    return (
      <div className="h-[40vh] w-full flex justify-center items-center p-10">
        <Empty description={error || (fetchError instanceof Error ? fetchError.message : 'Failed to load data') || 'Failed to load data'} />
      </div>
    );
  }

  return (
    <div>
  <p>
    In this section, the query gene, its query traits, and their related 
    child traits are systematically assessed across multiple evidence sources—
    including {" "}
    <a href="http://www.mulinlab.org/causaldb/index.html" target="_blank" className='underline '>Fine mapping</a>, 
    <a href="https://a2f.hugeamp.org/" target="_blank" className='underline ml-1'>PheWAS</a>, 
    <a href="https://ngdc.cncb.ac.cn/colocdb/home" target="_blank" className='underline ml-1'>Colocalisation</a>, 
    <a href="https://yanglab.westlake.edu.cn/smr-portal/" target="_blank" className='underline ml-1'>MR</a>, and 
    <a href="http://www.webtwas.net/#/browseGenes" target="_blank" className='underline ml-1'>TWAS</a> —
    to construct an integrated evidence scoring matrix.
  </p>
  <p>
    This approach enables additional gene–trait signals to emerge even when they are not 
    represented in the GWAS Catalog.
  </p>

    <div className="flex flex-col items-start gap-4">
      {uniqueCategories.length > 0 && (
        <div className="w-full mt-4">
          <div className="bg-white px-4 py-3 rounded border border-gray-200">
            <div className="font-bold text-center mb-3 text-xs">Categories</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {uniqueCategories.map((category) => {
                const categoryKey = Object.keys(categoryColors).find(
                  key => key.toLowerCase() === category.toLowerCase()
                );
                const color = categoryColors[category] || categoryColors[categoryKey] || '#95A5A6';
                return (
                  <div key={category} className="flex items-center text-xs">
                    <div
                      className="w-4 h-4 mr-2 flex-shrink-0 border border-gray-300"
                      style={{ backgroundColor: color }}
                    />
                    <span className="truncate">{category}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        
      )}

<div ref={heatmapRef} className="w-full" style={{ height: '500px' }} />
</div>
</div>
  );
};

export default HeatmapComponent;