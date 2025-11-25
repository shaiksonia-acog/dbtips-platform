import type React from "react"
import { useState, useEffect, useRef, memo } from "react"
import { Select, Input } from "antd"
import { Tooltip as AntdTooltip } from "antd"
import { InfoCircleOutlined } from "@ant-design/icons"
import { Chart, ScatterController, LinearScale, PointElement, Tooltip, Legend } from "chart.js"
import { Scatter } from "react-chartjs-2"
import { useQuery } from "react-query"
import { fetchData } from "../../utils/fetchData"
// import LoadingButton from "./loading"
import { Empty } from "antd"
import annotationPlugin from "chartjs-plugin-annotation"
const { Option } = Select
Chart.register(ScatterController, LinearScale, PointElement, Tooltip, annotationPlugin, Legend)

interface GeneEssentialityChartProps {
  target: string
}
interface TissueDropdownProps {
  tissues: string[]
  selectedTissues: string[]
  onTissueToggle: (tissues: string[]) => void
}
interface DataPoint {
  x: number
  y: number
  tissue: string
  cellLine: string
  depmapId: string
  disease: string
  expression: number | null
  cellLineName: string
  diseaseFromSource: string
  geneEffect: number
}
interface SearchBarProps {
  searchTerm: string
  onSearchChange: (value: string) => void
  searchField: keyof DataPoint
  onSearchFieldChange: (value: keyof DataPoint) => void
}

const SearchBar: React.FC<SearchBarProps> = ({ searchTerm, onSearchChange, searchField, onSearchFieldChange }) => {
  const selectBefore = (
    <Select value={searchField} onChange={(value) => onSearchFieldChange(value)} style={{ width: 150 }}>
      <Option value="depmapId">DepMap ID</Option>
      <Option value="cellLineName">Cell Line Name</Option>
      <Option value="diseaseFromSource">Disease</Option>
      <Option value="geneEffect">Gene Effect</Option>
      <Option value="expression">Expression</Option>
    </Select>
  )

  return (
    <div className="flex items-center gap-4">
      <Input
        addonBefore={selectBefore}
        value={searchTerm}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search..."
        style={{ width: 300 }}
      />
    </div>
  )
}

const TissueDropdown = memo(({ tissues, selectedTissues, onTissueToggle }: TissueDropdownProps) => {
  const handleChange = (selectedValues: string[]) => {
    onTissueToggle(selectedValues)
  }

  return (
    <div className="flex items-center gap-2">
      <span >Tissues: </span>
      <Select
        mode="multiple"
        maxTagCount="responsive"
        value={selectedTissues}
        onChange={handleChange}
        placeholder="Select tissues"
        style={{ width: 500 }}
        allowClear
        options={tissues
          .map((tissue) => ({ label: tissue, value: tissue }))
          .sort((a, b) => a.label.localeCompare(b.label))}
      />
    </div>
  )
})

const GeneEssentialityMap = ({ target }: GeneEssentialityChartProps) => {
  const [chartData, setChartData] = useState<any>(null)
  const [tissues, setTissues] = useState<string[]>([])
  const [selectedTissues, setSelectedTissues] = useState<string[]>([])
  const [originalData, setOriginalData] = useState<any>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [searchField, setSearchField] = useState<keyof DataPoint>("cellLineName")
  const chartRef = useRef<Chart<"scatter", any[], unknown> | null>(null)
  const [hiddenDatasets, setHiddenDatasets] = useState<boolean[]>(chartData?.datasets.map(() => false) || []);
  const [selectedPoint, setSelectedPoint] = useState<DataPoint | null>(null)
  const payload = {
    target: target,
  }
  const {
    data: geneMapData,
    error: geneMapError,
    isLoading: geneMapLoading,
  } = useQuery(["geneEssentialMap", payload], () => fetchData(payload, "/target-assessment/geneEssentialityMap/"), {
    enabled: !!target,
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000,
    refetchOnMount: false,
  })

  const isPointMatching = (point: DataPoint): boolean => {
    const matchesSearch =
      !searchTerm ||
      String(point[searchField] || "")
        .toLowerCase()
        .includes(searchTerm.toLowerCase())
    const matchesTissue = selectedTissues.length === 0 || selectedTissues.includes(point.tissue)
    return matchesSearch && matchesTissue
  }

  useEffect(() => {
    if(geneMapData?.geneEssentialityMap?.length == null) {
      setChartData(null)
      return
    }
    if (geneMapData) {
      const essentialityData = geneMapData?.geneEssentialityMap
      const uniqueTissues = Array.from(new Set(essentialityData.map((item: any) => item.tissueName))) as string[]
      uniqueTissues.sort((a, b) => b.toLowerCase().localeCompare(a.toLowerCase()))
      setTissues(uniqueTissues)

      const scatterData = essentialityData.flatMap((item: any) =>
        item.screens
          .filter((screen: any) => screen.geneEffect !== null)
          .map((screen: any) => ({
            x: screen.geneEffect,
            y: uniqueTissues.indexOf(item.tissueName),
            tissue: item.tissueName,
            cellLine: screen.cellLineName,
            depmapId: screen.depmapId,
            disease: screen.diseaseFromSource,
            expression: screen.expression,
            cellLineName: screen.cellLineName,
            diseaseFromSource: screen.diseaseFromSource,
            geneEffect: screen.geneEffect,
          })),
      )
      const negativeGeneEffect = scatterData.filter((point: DataPoint) => point.geneEffect <= -1)
      const positiveGeneEffect = scatterData.filter((point: DataPoint) => point.geneEffect > -1)

      const newChartData = {
        datasets: [
          {
            label: "Neutral",
            data: positiveGeneEffect,
            backgroundColor: positiveGeneEffect.map((point: DataPoint) => getPointColor(point)),
            borderColor: positiveGeneEffect.map((point: DataPoint) => getPointColor(point)),
            borderWidth: 1,
            pointHoverRadius: 8,
            pointRadius: positiveGeneEffect.map((point: DataPoint) => getPointRadius(point)),
            pointHoverBackgroundColor: "rgba(0, 0, 0, 0.8)",
            pointHoverBorderColor: "rgba(0, 0, 0, 1)",
            pointHoverBorderWidth: 2,
          },
          {
            label: "Dependency",
            data: negativeGeneEffect,
            backgroundColor: negativeGeneEffect.map((point: DataPoint) => getPointColor(point)),
            borderColor: negativeGeneEffect.map((point: DataPoint) => getPointColor(point)),
            borderWidth: 1,
            pointHoverRadius: 8,
            pointRadius: negativeGeneEffect.map((point: DataPoint) => getPointRadius(point)),
            pointHoverBackgroundColor: "rgba(0, 0, 0, 0.8)",
            pointHoverBorderColor: "rgba(0, 0, 0, 1)",
            pointHoverBorderWidth: 2,
          },
        ],
      }

      setChartData(newChartData)
      setOriginalData(newChartData)
    }
  }, [geneMapData])

  const handleSearchChange = (value: string) => {
    setSearchTerm(value)
  }
  const handleSearchFieldChange = (value: keyof DataPoint) => {
    setSearchField(value)
  }
  const handleTissueToggle = (tissues: string[]) => {
    setSelectedTissues(tissues)
  }

  const getPointColor = (point: DataPoint, isLegend = false) => {
    if (isLegend) {
      return point.geneEffect <= -1
        ? "rgba(113, 113, 122, 1)"
        : "rgba(59, 130, 246, 1)"
    }
    const matches = isPointMatching(point)
    const opacity = matches ? 0.8 : 0.05
    return point.geneEffect <= -1
      ? `rgba(239, 68, 68, ${opacity})`
      : `rgba(59, 130, 246, ${opacity})`
  }

  const getPointRadius = (point: DataPoint) => {
    const matches = isPointMatching(point)
    const isSelected = selectedPoint?.depmapId === point.depmapId
    if (isSelected) return 6
    return matches ? 5 : 4
  }

  useEffect(() => {
    if (originalData) {
      const neutralData = [...originalData.datasets[0].data]
      const dependencyData = [...originalData.datasets[1].data]

      setChartData({
        datasets: [
          {
            ...originalData.datasets[0],
            data: neutralData,
            backgroundColor: neutralData.map((point: DataPoint) => getPointColor(point)),
            borderColor: neutralData.map((point: DataPoint) => getPointColor(point, false)),
            pointRadius: neutralData.map((point: DataPoint) => getPointRadius(point)),
          },
          {
            ...originalData.datasets[1],
            data: dependencyData,
            backgroundColor: dependencyData.map((point: DataPoint) => getPointColor(point)),
            borderColor: dependencyData.map((point: DataPoint) => getPointColor(point, false)),
            pointRadius: dependencyData.map((point: DataPoint) => getPointRadius(point)),
          },
        ],
      })
    }
  }, [selectedTissues, searchTerm, searchField, originalData, selectedPoint])

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (_event: any, elements: any[]) => {
      if (elements.length > 0) {
        const dataIndex = elements[0].index
        const clickedPoint = chartData.datasets[0].data[dataIndex]
        setSelectedPoint((prevPoint) => (prevPoint?.depmapId === clickedPoint.depmapId ? null : clickedPoint))
      } else {
        setSelectedPoint(null)
      }
    },
    scales: {
      x: {
        title: {
          display: false,
          text: "Gene Effect",
          font: {
            size: 16,
            weight: "bold" as const,
            family: "Inter, sans-serif",
          },
          color: "#71717A",
        },
        ticks: {
          font: {
            size: 14,
            family: "Inter, sans-serif",
          },
          color: "#71717A",
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)",
        },
      },
      y: {
        title: {
          display: true,
          text: "Tissues",
          font: {
            size: 16,
            weight: "bold" as const,
            family: "Inter, sans-serif",
          },
          color: "#71717A",
        },
        ticks: {
          callback: (value: number) => tissues[value] || "",
          stepSize: 0.5,
          autoSkip: false,
          font: {
            size: 12,
            family: "Inter, sans-serif",
          },
          color: "#71717A",
        },
        grid: {
          color: "rgba(107, 109, 105,0.1)",
        },
      },
    },
    plugins: {
      tooltip: {
        enabled: true,
        intersect: true,
        external: (context: any) => {
          if (selectedPoint && context.tooltip.dataPoints) {
            const dataPoint = context.tooltip.dataPoints[0].raw
            if (dataPoint.depmapId === selectedPoint.depmapId) {
              context.tooltip.opacity = 1
            }
          }
        },
        callbacks: {
          label: (context: any) => {
            const point = context.raw
            return [
              `Tissue: ${point.tissue}`,
              `Cell Line: ${point.cellLine}`,
              `Gene Effect: ${point.x.toFixed(2)}`,
              `Disease: ${point.disease}`,
              `Expression: ${point.expression?.toFixed(2) || "N/A"}`,
              `DepMap ID: ${point.depmapId}`,
            ]
          },
        },
        backgroundColor: "rgba(0, 0, 0, 0.8)",
        titleColor: "rgba(255, 255, 255, 0.8)",
        bodyColor: "rgba(255, 255, 255, 0.8)",
        titleFont: {
          size: 14,
          weight: "bold" as const,
        },
        bodyFont: {
          size: 12,
        },
        padding: 12,
        cornerRadius: 8,
        borderColor: "rgba(255, 255, 255, 0.1)",
        borderWidth: 1,
      },
      annotation: {
        annotations: {
          line1: {
            type: "line" as const,
            yMin: -0.5,
            yMax: tissues.length - 0.5,
            xMin: -1,
            xMax: -1,
            borderColor: "rgba(239, 68, 68, 0.5)",
            borderWidth: 2,
            borderDash: [6, 6],
            label: {
              content: "Essentiality Threshold",
              enabled: true,
              font: {
                size: 14,
                weight: "bold" as const,
              },
              color: "rgba(239, 68, 68, 1)",
            },
          },
        },
      },
      legend: {
        display: false, // Disable default Chart.js legend
      },
    },
  }

  useEffect(() => {
    if (chartRef.current && selectedPoint) {
      const chart = chartRef.current
      const dataset = chart.data.datasets[0]
      const index = dataset.data.findIndex((point: DataPoint) => point.depmapId === selectedPoint.depmapId)

      if (index !== -1) {
        chart.setActiveElements([{ datasetIndex: 0, index }])
        const meta = chart.getDatasetMeta(0)
        chart.tooltip?.setActiveElements([{ datasetIndex: 0, index }], {
          x: meta.data[index].x,
          y: meta.data[index].y,
        })
        chart.update()
      }
    }
  }, [selectedPoint])

  // Custom legend click handler to toggle dataset visibility
const handleLegendClick = (datasetIndex: number) => {
  if (chartRef.current) {
    const chart = chartRef.current;
    const meta = chart.getDatasetMeta(datasetIndex);
    meta.hidden = !meta.hidden;
    chart.update();

    // Update React state
    setHiddenDatasets(prev => {
      const newState = [...prev];
      newState[datasetIndex] = meta.hidden;
      return newState;
    });
  }
}


  return (
    <div className="py-10" id="geneEssentialityMap">
      <h1 className="text-3xl font-semibold mb-3">Gene essentiality map</h1>
      <p className="mb-4 font-medium">
       Shows how essential  {target} is across multiple cell lines, helping identify genes that are critical for cell survival or specific to certain cancer types.
      </p>
      <div className="flex gap-2">
        <SearchBar
          searchTerm={searchTerm}
          onSearchChange={handleSearchChange}
          searchField={searchField}
          onSearchFieldChange={handleSearchFieldChange}
        />
        <TissueDropdown tissues={tissues} selectedTissues={selectedTissues} onTissueToggle={handleTissueToggle} />
      </div>
      {/* Custom Legend */}
      {chartData && (
        <div className="flex justify-center gap-4 mt-4">
          {chartData.datasets.map((dataset: any, index: number) => (
            <div
              key={dataset.label}
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => handleLegendClick(index)}
              style={{ opacity: chartRef.current?.getDatasetMeta(index).hidden ? 0.5 : 1 }}
            >
              <div
                className="w-11 h-3"
                style={{
                  backgroundColor: dataset.label === "Dependency" ? "rgba(113, 113, 122, 1)" : "rgba(59, 130, 246, 1)",
                }}
              />
              <span
                style={{
                  color:
                    dataset.label === "Dependency" || dataset.label === "Neutral"
                      ? "#71717A" // fully opaque gray, exactly like Dependency
                      : "#3b82f6", // blue for others
                          textDecoration: hiddenDatasets[index] && dataset.label === "Neutral" ? "line-through" : "none",

                      
                }}
              >
                {dataset.label}
              </span>
              {dataset.label === "Dependency" && (
                <AntdTooltip title=" Dependent cell lines are those in which a gene shows a probability of dependency greater than 0.5, meaning the gene is more likely to be essential for the cell’s survival or growth than nonessential.">
                  <span style={{ marginLeft: "4px", cursor: "pointer" }} aria-label="Dependency info">
                    <InfoCircleOutlined />
                  </span>
                </AntdTooltip>
              )}
            </div>
          ))}
        </div>
      )}
      {!geneMapLoading && geneMapError && (
        <div className="mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
          <Empty description={String(geneMapError)} />
        </div>
      )}
      {
        !geneMapLoading && !geneMapError && !chartData && (
          <div className="mt-4 h-[40vh]  flex items-center justify-center">
            <Empty description="No data available" />
          </div>
        )
      }
        {chartData && (
      <div className="flex-1 h-[70vh]">
          <div className="h-full w-full p-4">
            <Scatter data={chartData} options={chartOptions as any} ref={chartRef} />
            <div className="mt-2 flex items-center justify-center gap-2" aria-live="polite">
              <span className="text-m font-bold" style={{ color: "#71717A" }}>Gene Effect</span>
              <AntdTooltip
                title="Indicates how essential a gene is for a cell line’s survival. Lower scores mean higher dependency: with 0 = nonessential and -1 = median of common essential genes."
                placement="top"
              >
                <button type="button" className="inline-flex items-center" aria-label="About Gene Effect">
                  <InfoCircleOutlined />
                </button>
              </AntdTooltip>
            </div>
          </div>
      </div>
        )}
    </div>
  )
}

export default GeneEssentialityMap