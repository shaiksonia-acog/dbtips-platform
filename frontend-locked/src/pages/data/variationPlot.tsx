import { useState, useEffect, useRef, memo, useMemo, useCallback } from "react";
import Plotly from "plotly.js-dist-min";
import { Select, message, Empty, Space, Tooltip } from "antd";
import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import LoadingButton from "../../components/loading";
import CHROMOSOMES from "./chromosomes.json";
import { InfoCircleOutlined } from "@ant-design/icons";

const { Option } = Select;

function DiseasePlot({ diseases, diseaseAreaFilter }) {
  const plotRef = useRef(null);
  const isPlottingRef = useRef(false);
  
  const [selectedDisease, setSelectedDisease] = useState("");
  const [mondoId, setMondoId] = useState(null);
  const [rawData, setRawData] = useState([]);
  const [variantOptions, setVariantOptions] = useState([]);
  const [geneOptions, setGeneOptions] = useState([]);
  const [selectedOption, setSelectedOption] = useState(null);
  const [filterType, setFilterType] = useState("gene");

  // Reset data on disease change
  useEffect(() => {
    setMondoId(null);
    setRawData([]);
    setVariantOptions([]);
    setGeneOptions([]);
    setSelectedOption(null);
  }, [selectedDisease]);

  const handleDiseaseChange = useCallback((value) => {
    setSelectedDisease(value);
  }, []);

  const handleFilterTypeChange = useCallback((value) => {
    setFilterType(value);
    setSelectedOption(null);
  }, []);

  const handleOptionChange = useCallback((value) => {
    setSelectedOption(value);
  }, []);

  const payload = useMemo(() => ({ diseases: [selectedDisease] }), [selectedDisease]);

  const { data: locuszoomData, error: locuszoomError, isLoading: locuszoomLoading } = useQuery(
    ["locuszoom", payload],
    () => fetchData(payload, "/genomics/gwas-associations"),
    {
      enabled: selectedDisease !== "",
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  useEffect(() => {
    if (locuszoomData) {
      if (locuszoomData?.[selectedDisease.toLowerCase()] !== "EFO ID not found for immune-mediated necrotizing myopathy") {
        const id = locuszoomData?.[selectedDisease.toLowerCase()]?.split("/").pop();
        setMondoId(id);
      }
    }
  }, [locuszoomData, selectedDisease]);

  const processFileData = useCallback((data) => {
    const rows = data.split("\n").map((row) => row.split("\t"));
    const headers = rows.shift();
    const chrIndex = headers.indexOf("Chromosome");
    const posIndex = headers.indexOf("Position");
    const pvalIndex = headers.indexOf("pvalue");
    const rsidIndex = headers.indexOf("rsID");
    const refAlleleIndex = headers.indexOf("Variant and Risk Allele");
    const authorIndex = headers.indexOf("Author");
    const pubmedidIndex = headers.indexOf("PubMed ID");
    const mappedgeneIndex = headers.indexOf("Mapped gene(s)");
    const reportedtraitIndex = headers.indexOf("Reported trait");
    const mapped_traitIndex = headers.indexOf("Mapped Trait");
    const studyAccesionIndex = headers.indexOf("Study Accession");

    if ([chrIndex, posIndex, pvalIndex, rsidIndex, refAlleleIndex, authorIndex, pubmedidIndex, mappedgeneIndex, mapped_traitIndex, studyAccesionIndex].includes(-1)) {
      message.error("Required columns not found in TSV file.");
      return;
    }

    const processedRows = rows
      .filter(row => row.length >= headers.length)
      .map(row => ({
        chr: row[chrIndex],
        pos: parseInt(row[posIndex]),
        pval: row[pvalIndex],
        rsID: row[rsidIndex],
        variant: row[refAlleleIndex],
        author: row[authorIndex],
        pubmedid: row[pubmedidIndex],
        gene: row[mappedgeneIndex],
        reportedtrait: row[reportedtraitIndex],
        logPval: -Math.log10(parseFloat(row[pvalIndex])),
        mapped_trait: row[mapped_traitIndex]
      }));

    setRawData(processedRows);

    const uniqueVariants = [...new Set(processedRows.map(row => row.variant))].filter(Boolean).sort();
    const uniqueGenes = [
      ...new Set(
        processedRows.flatMap(row => row.gene ? row.gene.split(/[,;]+/) : [])
      )
    ].filter(gene => typeof gene === 'string' && gene.trim() !== '').sort();

    setVariantOptions(uniqueVariants.map(variant => ({ label: variant, value: variant })));
    setGeneOptions(uniqueGenes.map(gene => ({ label: gene, value: gene })));
  }, []);

  useEffect(() => {
    if (!mondoId) return;

    const url = `${import.meta.env.VITE_API_URI}/api/download/${mondoId}`;

    fetch(url)
      .then((response) => response.text())
      .then((text) => {
        processFileData(text);
      })
      .catch((error) => {
        message.error("Error fetching data for the disease.");
        console.error("Error fetching TSV:", error);
      });
  }, [mondoId, processFileData]);

  // Memoized filtered data
  const filteredData = useMemo(() => {
    if (!rawData.length) return [];

    let filtered = [...rawData];

    if (selectedOption) {
      if (filterType === "variant") {
        filtered = filtered.filter(row => row.variant === selectedOption);
      } else if (filterType === "gene") {
        filtered = filtered.filter((row) => {
          const genes = row.gene ? row.gene.split(/[;,]+/).map((g) => g.trim()) : [];
          return genes.some((gene) => gene === selectedOption.trim());
        });
      }
    }

    return filtered;
  }, [rawData, selectedOption, filterType]);

  const renderManhattanPlot = useCallback((data) => {
    const plotDiv = plotRef.current;
    if (!plotDiv || isPlottingRef.current) return;
    
    isPlottingRef.current = true;

    const dataMap = {};

    data.forEach((row) => {
      const { chr, pos, logPval, rsID, variant, gene, author, pubmedid, reportedtrait, pval } = row;

      if (!dataMap[chr]) {
        dataMap[chr] = { x: [], y: [], text: [], positions: [], locusX: [] };
      }

      const chromosome = CHROMOSOMES.chromosomes.find((c) => c.name === chr);
      const location = chromosome ? parseFloat(chromosome?.location.toString()) : 0;
      const xValue = location + pos;

      dataMap[chr].x.push(xValue);
      dataMap[chr].y.push(logPval);
      dataMap[chr].locusX.push(chr);
      dataMap[chr].text.push(
        `rsID: ${rsID}<br>Chromosome: ${chr}<br>P-value: ${pval}<br>` +
        `Variant and Risk Allele: ${variant}<br>Mapped Gene(s): ${gene}<br>` +
        `Reported Trait: ${reportedtrait}<br>Author: ${author}<br>PubMed ID: ${pubmedid}`
      );
      dataMap[chr].positions.push(pos);
    });

    // Clean up previous plot completely
    Plotly.purge(plotDiv);

    const traces = Object.keys(dataMap).map((chr) => ({
      x: dataMap[chr].x,
      y: dataMap[chr].y,
      mode: "markers",
      type: "scatter",
      name: `Chr ${chr}`,
      text: dataMap[chr].text,
      hoverinfo: "text",
      marker: { size: 6 },
      customdata: dataMap[chr].positions,
      locusX: dataMap[chr].locusX,
    }));

    const layout = {
      title: {
        text: "Manhattan Plot with Variant Details",
      },
      xaxis: {
        title: {
          text: "Chromosome",
        },
        tickvals: CHROMOSOMES.chromosomes.map((d) => d.location + d.length / 2),
        ticktext: CHROMOSOMES.chromosomes.map((d) => d.name),
      },
      shapes: [
        {
          type: 'line',
          x0: 0,
          x1: 3199026875,
          y0: 8,
          y1: 8,
          line: {
            color: 'grey',
            dash: 'dash',
            width: 2,
          },
        },
      ],
      yaxis: {
        title: {
          text: "-log10(p-value)",
        },
      },
      hovermode: "closest",
      showlegend: false,
    };

    const config = {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      // Disable scroll zoom to prevent interference with page scrolling
      scrollZoom: false,
    };

    Plotly.newPlot(plotDiv, traces, layout, config).then(() => {
      isPlottingRef.current = false;
    });
  }, []);

  useEffect(() => {
    if (filteredData.length > 0) {
      // Use requestAnimationFrame to defer plotting
      requestAnimationFrame(() => {
        renderManhattanPlot(filteredData);
      });
    }
  }, [filteredData, renderManhattanPlot]);

  useEffect(() => {
    if (diseases && diseases.length > 0) {
      setSelectedDisease(diseases[0]);
    }
  }, [diseases]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (plotRef.current) {
        Plotly.purge(plotRef.current);
      }
    };
  }, []);

  const getCurrentOptions = useCallback(() => {
    return filterType === "variant" ? variantOptions : geneOptions;
  }, [filterType, variantOptions, geneOptions]);

  return (
    <div>
      <h2 className="text-xl subHeading font-semibold mb-3 mt-4" id="manhattanPlot">Manhattan Plot</h2>
      <p className="my-1 font-medium">
        Displays genome-wide SNP associations, highlighting significant genetic loci linked to {diseases}.
      </p>

      <div className="flex flex-wrap gap-2 mt-4">
        <div className="flex items-center">
          <span className="mr-1">{diseaseAreaFilter ? "Disease area" : "Disease"}</span>
          <Select
            style={{ width: 300 }}
            placeholder="Select a disease"
            onChange={handleDiseaseChange}
            value={selectedDisease}
            loading={locuszoomLoading}
          >
            {diseases.map((disease) => (
              <Option key={disease} value={disease}>
                {disease}
              </Option>
            ))}
          </Select>
        </div>

        {(variantOptions.length > 0 || geneOptions.length > 0) && (
          <div className="flex items-center ml-4">
            <span className="mr-1">Filter: </span>
            <Space.Compact>
              <Select
                style={{ width: 200 }}
                value={filterType}
                onChange={handleFilterTypeChange}
                options={[
                  { value: 'variant', label: 'Variant and risk allele' },
                  { value: 'gene', label: 'Gene' }
                ]}
              />
              <Select
                style={{ width: 250 }}
                placeholder={`Select ${filterType}`}
                onChange={handleOptionChange}
                value={selectedOption}
                allowClear
                showSearch
                filterOption={(input, option) =>
                  option.label.toLowerCase().includes(input.toLowerCase())
                }
                options={getCurrentOptions()}
              />
            </Space.Compact>
          </div>
        )}
      </div>

      {locuszoomLoading && <LoadingButton />}
      {locuszoomError && <Empty description="Failed to load data" />}
      {!locuszoomLoading && !locuszoomError && locuszoomData?.[selectedDisease.toLowerCase()] === null && (
        <div className="h-[40vh] flex justify-center items-center">
          <Empty description="No data available" />
        </div>
      )}
      {locuszoomData?.[selectedDisease.toLowerCase()] === "EFO ID not found for immune-mediated necrotizing myopathy" && (
        <div className="h-[40vh] flex justify-center items-center">
          <Empty description="No data available" />
        </div>
      )}

      {!locuszoomLoading && !locuszoomError && locuszoomData?.[selectedDisease.toLowerCase()] && 
       locuszoomData?.[selectedDisease.toLowerCase()] !== "EFO ID not found for immune-mediated necrotizing myopathy" && (
        <div style={{ position: 'relative', willChange: 'transform' }}>
          <div
            id="plot"
            ref={plotRef}
            style={{ 
              width: "100%", 
              height: "400px", 
              marginTop: "20px",
              // Force GPU acceleration
              transform: 'translateZ(0)',
              backfaceVisibility: 'hidden'
            }}
          >
            <Tooltip title="Each number represents a chromosome (1–22, X, Y). Dots along each chromosome mark SNP locations">
              <InfoCircleOutlined
                style={{
                  position: 'absolute',
                  bottom: '25px',
                  left: '53.8%',
                  fontSize: '16px',
                  color: '#666',
                  cursor: 'pointer'
                }}
              />
            </Tooltip>
            <Tooltip title="Indicates the statistical significance of each SNP's association with the disease. Higher points mean stronger associations.">
              <InfoCircleOutlined
                style={{
                  position: 'absolute',
                  top: '39%',
                  left: '28px',
                  fontSize: '16px',
                  color: '#666',
                  cursor: 'pointer',
                  transform: 'translateY(-80%) rotate(-90deg)'
                }}
              />
            </Tooltip>
          </div>
          <div id="lz-plot" style={{ marginTop: "20px" }}></div>
        </div>
      )}
    </div>
  );
}

export default memo(DiseasePlot);