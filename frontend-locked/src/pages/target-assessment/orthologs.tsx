import { useMemo, useState } from 'react'
import { useQuery } from 'react-query';
import { fetchData } from '../../utils/fetchData';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ConfigProvider, Empty, Segmented } from 'antd';
import { List, ChartLine } from 'lucide-react';
import Table from '../../components/table';



const Ortholog = ({target}) => {
    const [hoveredGene, setHoveredGene] = useState(null);
    const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
   
    // const leftChartData = [];
    // const rightChartData = [];
    const payload = {
        target: target,
    };

	const {
		data: orthologData,
		error: orthologError,
		isLoading: orthologLoading,
	} = useQuery(
		['orthologs', payload],
		() => fetchData(payload, '/target-assessment/orthologs/'),
		{
			enabled: !!target ,
		}
	);
    // const chartData = [];
    const speciesOrder = useMemo(() => {
        if (!orthologData?.orthologs) return [];
        const uniqueSpecies = [...new Set(orthologData?.orthologs.map(item => item.speciesName))];
        return uniqueSpecies;
      }, [orthologData]);
      const speciesIndexMap = useMemo(() => {
        const map: { [key: string]: number } = {};
        speciesOrder.forEach((name: string, idx) => {
          map[name] = speciesOrder.length - 1 - idx;
        });
        return map;
      }, [speciesOrder]);
      const { leftChartData, rightChartData } = useMemo(() => {
        const left = [];
        const right = [];
        
        orthologData?.orthologs.forEach(item => {
          const species = item.speciesName;
          const yPos = speciesIndexMap[species];
          const geneKey = `${species}-${item.homologue}`;
          
          // Left side - Query percentage
          left.push({
            x: item.query_percentage,
            y: yPos,
            homologue: item.homologue,
            species: species,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
      
          // Right side - Target percentage
          right.push({
            x: item.target_percentage,
            y: yPos,
            homologue: item.homologue,
            species: species,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
        });
  
        return { leftChartData: left, rightChartData: right };
      }, [orthologData, speciesIndexMap]);
    
      const colorMap = {
        "other_paralog": "#6B9BD1",
        "within_species_paralog": "#4A7BA7",
        "ortholog_one2one": "#6B9BD1"
      };
    
      const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
          const data = payload[0].payload;
          return (
            <div className="bg-white p-3 shadow-lg rounded-lg border-2 border-blue-400">
                              <p ><span className='className="text-sm font-semibold text-gray-600 mt-1"'>Type: </span> {data.homologyType}</p>

              <p > <span className='className="text-sm font-semibold text-gray-600 mt-1"'>Homolog:</span> {data.homologue}</p>
              <p ><span className='className="text-sm font-semibold text-gray-600 mt-1"'>Species: </span>{data.species}</p>
              <p >
              <span className='className="text-sm font-semibold text-gray-600 mt-1"'>Query: </span>
                {data.queryPct}
              </p>
              <p >
              <span className='className="text-sm font-semibold text-gray-600 mt-1"'>Target:</span>
                 {data.targetPct}
              </p>
            </div>
          );
        }
        return null;
      };
    
      const handleMouseEnter = (data) => {
        setHoveredGene(data.geneKey);
      };
    
      const handleMouseLeave = () => {
        setHoveredGene(null);
      };

      const tableRowData = useMemo(() => {
        if (!orthologData?.orthologs) return [];
        return orthologData.orthologs.map(item => ({
          homologue: item.homologue,
          speciesName: item.speciesName,
          homologyType: item.homologyType.replace(/_/g, ' '),
          queryPercentage: item.query_percentage.toFixed(2) + '%',
          targetPercentage: item.target_percentage.toFixed(2) + '%',
        }));
      }, [orthologData]);

      const tableColumnDefs = useMemo(() => [
        {
            field: 'speciesName',
            headerName: 'Species',
            filter: true,
            sortable: true,
            flex: 1,
          },
          {
            field: 'homologyType',
            headerName: 'Homology Type',
            filter: true,
            sortable: true,
            flex: 1,
          },
        {
          field: 'homologue',
          headerName: 'Homologue',
          filter: true,
          sortable: true,
          flex: 1,
        },
       
       
        {
          field: 'queryPercentage',
          headerName: 'Query % Identity',
          filter: true,
          sortable: true,
          flex: 1,
        },
        {
          field: 'targetPercentage',
          headerName: 'Target % Identity',
          filter: true,
          sortable: true,
          flex: 1,
        },
      ], []);
  
      const yTicks = speciesOrder.map((_, idx) => idx);
      const xTicks = Array.from({ length: 11 }, (_, i) => i * 10);
      const yDomain = [-0.5, speciesOrder.length - 0.5];
      return (
        <div className="px-[5vw] py-20 bg-gray-50 " id="orthologs">
          <div className="mb-4 ">
          <h1 className='text-3xl font-semibold'>Comparative genomics/Orthologs</h1>
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
									value: "table",
									icon: <List />,
								},
								{
									label: "",
									value: "chart",
									icon: <ChartLine className="w-5 h-5 mt-1"/>,
								}
								
							]}
							value={viewMode}
							onChange={(value) => setViewMode(value as "chart" | "table")}
						/>
					</ConfigProvider>
				</div>
			</div>

            {orthologLoading ? (
              <div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
                <Empty description="Loading data..." />
              </div>
            ) : orthologError || !orthologData?.orthologs || orthologData.orthologs.length === 0 ? (
              <div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
                <Empty description="No data available" />
              </div>
            ) : (
              <>
                {viewMode === "chart" && (
                  <div className="flex justify-center items-start w-full" style={{ height: "500px" }}>

                    {/* LEFT CHART (Query) */}
                    <div style={{ width: "45%", height: "100%", position: "relative" }}>
                      <ResponsiveContainer>
                        <ScatterChart margin={{ top: 20, right: 10, bottom: 50, left: 80 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                          <XAxis
                            type="number"
                            dataKey="x"
                            domain={[0, 100]}
                            ticks={xTicks}
                            label={{
                              value: "Query Percentage Identity →",
                              position: "insideBottom",
                              offset: -10,
                            }}
                          />
                          <YAxis
                            type="number"
                            dataKey="y"
                            domain={yDomain}
                            ticks={yTicks}
                            tickLine={false}
                            tick={false}
                            axisLine={false}
                          />
                          <Tooltip content={<CustomTooltip active={undefined} payload={undefined} />} cursor={{ strokeDasharray: '3 3' }} />
                          <Scatter
                            data={leftChartData}
                            shape={(props) => {
                              const { cx, cy, payload } = props;
                              const isHovered = hoveredGene === payload.geneKey;
                              const radius = isHovered ? 8 : 5;
                              return (
                                <circle
                                  cx={cx}
                                  cy={cy}
                                  r={radius}
                                  fill={colorMap[payload.homologyType]}
                                  fillOpacity={isHovered ? 1 : 0.7}
                                  onMouseEnter={() => handleMouseEnter(payload)}
                                  onMouseLeave={handleMouseLeave}
                                  style={{ cursor: 'pointer' }}
                                />
                              );
                            }}
                          />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>

                    {/* CENTER SPECIES LABELS */}
                    <div style={{ 
                      width: "10%", 
                      height: "100%",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "center",
                      paddingTop: "20px",
                      paddingBottom: "70px"
                    }}>
                      <div style={{ 
                        display: "flex", 
                        flexDirection: "column", 
                        justifyContent: "space-around",
                        height: "100%"
                      }}>
                        {speciesOrder.map((sp) => (
                          <div key={sp as string} className="text-gray-800 font-semibold text-center" style={{ 
                            flex: 1,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center"
                          }}>
                            {sp as string}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* RIGHT CHART (Target) */}
                    <div style={{ width: "45%", height: "100%" }}>
                      <ResponsiveContainer>
                        <ScatterChart margin={{ top: 20, right: 80, bottom: 50, left: 10 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                          <XAxis
                            type="number"
                            dataKey="x"
                            domain={[0, 100]}
                            ticks={xTicks}
                            reversed
                            label={{
                              value: "← Target Percentage Identity",
                              position: "insideBottom",
                              offset: -10,
                            }}
                          />
                          <YAxis
                            type="number"
                            dataKey="y"
                            domain={yDomain}
                            ticks={yTicks}
                            tickLine={false}
                            tick={false}
                            axisLine={false}
                          />
                          <Tooltip content={<CustomTooltip active={undefined} payload={undefined} />} cursor={{ strokeDasharray: '3 3' }} />
                          <Scatter
                            data={rightChartData}
                            shape={(props) => {
                              const { cx, cy, payload } = props;
                              const isHovered = hoveredGene === payload.geneKey;
                              const radius = isHovered ? 8 : 5;
                              return (
                                <circle
                                  cx={cx}
                                  cy={cy}
                                  r={radius}
                                  fill={colorMap[payload.homologyType]}
                                  fillOpacity={isHovered ? 1 : 0.7}
                                  onMouseEnter={() => handleMouseEnter(payload)}
                                  onMouseLeave={handleMouseLeave}
                                  style={{ cursor: 'pointer' }}
                                />
                              );
                            }}
                          />
                        </ScatterChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {viewMode === "table" && (
                  <div className='ag-theme-quartz mt-4 h-[80vh] max-h-[720px]'>
                    <Table
                      
                      columnDefs={tableColumnDefs}
                      rowData={tableRowData}
                    />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      );
  }
  


export default Ortholog
