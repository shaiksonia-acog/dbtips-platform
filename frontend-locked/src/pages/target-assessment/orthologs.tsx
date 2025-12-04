import { useMemo, useState } from 'react'
import { useQuery } from 'react-query';
import { fetchData } from '../../utils/fetchData';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ConfigProvider, Empty, Segmented } from 'antd';
import { List, ChartLine } from 'lucide-react';
import Table from '../../components/table';
import LoadingButton from '../../components/loading';

const labels = {
    6239: "Caenorhabditis elegans (Nematode, N2)",
    7227: "Drosophila melanogaster (Fruit fly)",
    7955: "Zebrafish",
    8364: "Tropical clawed frog",
    9823: "Pig",
    9615: "Dog",
    10141: "Guinea Pig",
    9986: "Rabbit",
    10116: "Rat",
    10090: "Mouse",
    9544: "Macaque",
    9598: "Chimpanzee",
    9606: "Human",
  };


const Ortholog = ({target}) => {
    const [hoveredGeneOrtholog, setHoveredGeneOrtholog] = useState(null);
    const [hoveredGeneParalog, setHoveredGeneParalog] = useState(null);
    const [orthologViewMode, setOrthologViewMode] = useState<"chart" | "table">("chart");
    const [paralogViewMode, setParalogViewMode] = useState<"chart" | "table">("chart");
   
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
    
    // Filter data for Orthologs
    const orthologsData = useMemo(() => {
        if (!orthologData?.orthologs) return [];
        return orthologData.orthologs.filter(item => item.homologyType.toLowerCase().includes("ortholog"));
    }, [orthologData]);

    // Filter data for Paralogs
    const paralogsData = useMemo(() => {
        if (!orthologData?.orthologs) return [];
        return orthologData.orthologs.filter(item => item.homologyType.toLowerCase().includes("paralog"));
    }, [orthologData]);

    // Species data for Orthologs
    const orthologSpeciesOrder = useMemo(() => {
        const uniqueSpeciesIds = [...new Set(orthologsData.map(item => item.speciesId))];
        return uniqueSpeciesIds;
    }, [orthologsData]);

    const orthologSpeciesIndexMap = useMemo(() => {
        const map: { [key: string]: number } = {};
        orthologSpeciesOrder.forEach((id: string, idx) => {
          map[id] = orthologSpeciesOrder.length - 1 - idx;
        });
        return map;
    }, [orthologSpeciesOrder]);

    // Species data for Paralogs
    const paralogSpeciesOrder = useMemo(() => {
        const uniqueSpeciesIds = [...new Set(paralogsData.map(item => item.speciesId))];
        return uniqueSpeciesIds;
    }, [paralogsData]);

    const paralogSpeciesIndexMap = useMemo(() => {
        const map: { [key: string]: number } = {};
        paralogSpeciesOrder.forEach((id: string, idx) => {
          map[id] = paralogSpeciesOrder.length - 1 - idx;
        });
        return map;
    }, [paralogSpeciesOrder]);

    // Chart data for Orthologs
    const { orthologLeftChartData, orthologRightChartData } = useMemo(() => {
        const left = [];
        const right = [];

        orthologsData.forEach(item => {
          const speciesId = item.speciesId;
          const speciesName = item.speciesName;
          const yPos = orthologSpeciesIndexMap[speciesId];
          const geneKey = `${speciesId}-${item.homologue}`;
          
          left.push({
            x: item.query_percentage,
            y: yPos,
            homologue: item.homologue,
            species: speciesName,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
      
          right.push({
            x: item.target_percentage,
            y: yPos,
            homologue: item.homologue,
            species: speciesName,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
        });
  
        return { orthologLeftChartData: left, orthologRightChartData: right };
    }, [orthologsData, orthologSpeciesIndexMap]);

    // Chart data for Paralogs
    const { paralogLeftChartData, paralogRightChartData } = useMemo(() => {
        const left = [];
        const right = [];

        paralogsData.forEach(item => {
          const speciesId = item.speciesId;
          const speciesName = item.speciesName;
          const yPos = paralogSpeciesIndexMap[speciesId];
          const geneKey = `${speciesId}-${item.homologue}`;
          
          left.push({
            x: item.query_percentage,
            y: yPos,
            homologue: item.homologue,
            species: speciesName,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
      
          right.push({
            x: item.target_percentage,
            y: yPos,
            homologue: item.homologue,
            species: speciesName,
            homologyType: item.homologyType,
            queryPct: item.query_percentage,
            targetPct: item.target_percentage,
            geneKey: geneKey
          });
        });
  
        return { paralogLeftChartData: left, paralogRightChartData: right };
    }, [paralogsData, paralogSpeciesIndexMap]);
    
    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
          const data = payload[0].payload;
          return (
            <div className="bg-white p-3 shadow-lg rounded-lg border-2 border-blue-400">
              <p><span className='text-sm font-semibold text-gray-600 mt-1'>Type: </span> {data.homologyType}</p>
              <p><span className='text-sm font-semibold text-gray-600 mt-1'>Homolog:</span> {data.homologue}</p>
              <p><span className='text-sm font-semibold text-gray-600 mt-1'>Species: </span>{data.species}</p>
              <p>
                <span className='text-sm font-semibold text-gray-600 mt-1'>Query: </span>
                {data.queryPct}
              </p>
              <p>
                <span className='text-sm font-semibold text-gray-600 mt-1'>Target:</span>
                {data.targetPct}
              </p>
            </div>
          );
        }
        return null;
    };

    // Table data for Orthologs
    const orthologTableRowData = useMemo(() => {
        return orthologsData.map(item => ({
          homologue: item.homologue,
          speciesName: item.speciesName,
          homologyType: item.homologyType.replace(/_/g, ' '),
          queryPercentage: item.query_percentage.toFixed(2) + '%',
          targetPercentage: item.target_percentage.toFixed(2) + '%',
        }));
    }, [orthologsData]);

    // Table data for Paralogs
    const paralogTableRowData = useMemo(() => {
        return paralogsData.map(item => ({
          homologue: item.homologue,
          speciesName: item.speciesName,
          homologyType: item.homologyType.replace(/_/g, ' '),
          queryPercentage: item.query_percentage.toFixed(2) + '%',
          targetPercentage: item.target_percentage.toFixed(2) + '%',
        }));
    }, [paralogsData]);

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
  
    const xTicks = Array.from({ length: 11 }, (_, i) => i * 10);

    const renderToggle = (viewMode: "chart" | "table", setViewMode: (mode: "chart" | "table") => void) => {
        return (
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
        );
    };

    const renderChartSection = (
        title: string,
        leftData: any[],
        rightData: any[],
        speciesOrder: any[],
        hoveredGene: string | null,
        setHoveredGene: (gene: string | null) => void
    ) => {
        if (leftData.length === 0) {
            return (
                <div className='flex items-center justify-center h-40 bg-white rounded-lg'>
                    <Empty description={`No ${title.toLowerCase()} data available`} />
                </div>
            );
        }

        const yTicks = speciesOrder.map((_, idx) => idx);
        const yDomain = [-0.5, speciesOrder.length - 0.5];

        const handleMouseEnter = (data) => {
            setHoveredGene(data.geneKey);
        };

        const handleMouseLeave = () => {
            setHoveredGene(null);
        };

        return (
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
                        data={leftData}
                        shape={(props) => {
                          const { cx, cy, payload } = props;
                          const isHovered = hoveredGene === payload.geneKey;
                          const radius = isHovered ? 8 : 5;
                          return (
                            <circle
                              cx={cx}
                              cy={cy}
                              r={radius}
                              fill={"#4A7BA7"}
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
                  width: "25%", 
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
                    {speciesOrder.map((spId) => (
                      <div key={String(spId)} className="text-gray-800 font-semibold text-center"
                        style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        {labels[spId as keyof typeof labels] || String(spId)}
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
                        data={rightData}
                        shape={(props) => {
                          const { cx, cy, payload } = props;
                          const isHovered = hoveredGene === payload.geneKey;
                          const radius = isHovered ? 8 : 5;
                          return (
                            <circle
                              cx={cx}
                              cy={cy}
                              r={radius}
                              fill={"#4A7BA7"}
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
        );
    };

    const renderTableSection = (rowData: any[]) => {
        if (rowData.length === 0) {
            return (
                <div className='flex items-center justify-center h-40 bg-white rounded-lg'>
                    <Empty description={`No data available`} />
                </div>
            );
        }

        return (
            <div className=' '>
                <Table
                  columnDefs={tableColumnDefs}
                  rowData={rowData}
                />
            </div>
        );
    };

    return (
        <div className="px-[5vw] py-20 bg-gray-50" id="Comparative genomics">
          <div className="mb-4">
            <div className='mb-8'>
              <h1 className='text-3xl font-semibold'>Comparative genomics</h1>
              <p className='mb-2'>Comparative genomics  - examines orthologous and paralogous relationships across species to assess sequence conservation, divergence, and potential functional overlap.</p>
            </div>

            {orthologLoading ? (
              <div className=' flex items-center justify-center'>
                <LoadingButton/>
              </div>
            ) : orthologError || !orthologData?.orthologs || orthologData.orthologs.length === 0 ? (
              <div className='ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center'>
                <Empty description="No data available" />
              </div>
            ) : (
              <>
                {/* Orthologs Section */}
                <div className="mb-12" id="orthologs">
                    <h2 className="text-xl subHeading font-semibold">Orthologs</h2>
                    <p>Orthology analysis identifies sequence elements conserved across species through shared ancestry, helping validate therapeutic targets by revealing evolutionary preservation of function. </p>
                  <div className='flex justify-between items-center mb-3'>
                    <div></div>
                    {renderToggle(orthologViewMode, setOrthologViewMode)}
                  </div>
                  {orthologViewMode === "chart" ? 
                    renderChartSection(
                      "Orthologs",
                      orthologLeftChartData,
                      orthologRightChartData,
                      orthologSpeciesOrder,
                      hoveredGeneOrtholog,
                      setHoveredGeneOrtholog
                    ) : 
                    renderTableSection(orthologTableRowData)
                  }
                </div>

                {/* Paralogs Section */}
                <div className="mb-12" id='paralogs'>
                    <h2 className="text-xl subHeading font-semibold">Paralogs</h2>
                    <p>Paralog assessment identifies structurally similar proteins within the same species that may share binding sites with the target, helping predict off-target interactions and possible side effects.</p>
                  <div className='flex justify-between items-center mb-3'>
                    <div></div>
                    {renderToggle(paralogViewMode, setParalogViewMode)}
                  </div>
                  {paralogViewMode === "chart" ? 
                    renderChartSection(
                      "Paralogs",
                      paralogLeftChartData,
                      paralogRightChartData,
                      paralogSpeciesOrder,
                      hoveredGeneParalog,
                      setHoveredGeneParalog
                    ) : 
                    renderTableSection(paralogTableRowData)
                  }
                </div>
              </>
            )}
          </div>
          {/* <Paralogs target={target} /> */}
        </div>
    );
}

export default Ortholog;