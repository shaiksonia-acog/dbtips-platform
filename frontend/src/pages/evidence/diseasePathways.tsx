import React, { useState, useEffect } from "react";
import { Empty, Select, Collapse, theme } from "antd";
import { CaretRightOutlined } from "@ant-design/icons";
import { useQuery } from "react-query";
import LoadingButton from "../../components/loading";
import CarouselComponent from "./carousel";
import { fetchData } from "../../utils/fetchData";
import { capitalizeFirstLetter } from "../../utils/helper";

// TypeScript Interfaces
interface GeneResult {
  gene_symbols: string[];
  url?: string;
  pmcid?: string;
  figtitle?: string;
  figid?: string;
  image_url?: string;
  pmid?: string;
  drugs?: string;
  keywords?: string;
  process?: string;
  insights?: string;
  data_source?: string;
}

interface NetworkBiologyData {
  [disease: string]: {
    results: GeneResult[];
  };
}

interface FilteredDiseaseData {
  disease: string;
  results: GeneResult[];
}

interface NetworkBiologyProps {
  indications: string[];
  target?: string;
}

const DiseasePathways: React.FC<NetworkBiologyProps> = ({ indications, target }) => {
  const { token } = theme.useToken();
  const [selectedTarget, setSelectedTarget] = useState<string | undefined>(
    target?.toUpperCase()
  );
  const [filteredData, setFilteredData] = useState<FilteredDiseaseData[]>([]);
  const [geneSet, setGeneSet] = useState<string[]>([]);
  const [summary, setSummary] = useState<React.ReactNode>(null);

  // Set initial target when component mounts or target prop changes
  useEffect(() => {
    if (target) {
      setSelectedTarget(target.toUpperCase());
    }
  }, [target]);

  // Determine which endpoint and payload to use based on whether we have a target AND indications
  const getQueryConfig = () => {
    const hasTarget = target && target.trim().length > 0;
    const hasIndications = indications && indications.length > 0;

    if (hasTarget && hasIndications) {
      // Use target-literature-images endpoint only when we have BOTH target AND diseases
      return {
        endpoint: "/evidence/target-literature-images/",
        payload: { 
          target: target, 
          diseases: indications
        },
        queryKey: ["DiseasePathways-Target", target, indications]
      };
    } else if (!hasTarget && hasIndications) {
      // Use literature-images endpoint for disease-only queries
      return {
        endpoint: "/evidence/literature-images/",
        payload: { diseases: indications },
        queryKey: ["DiseasePathways-Disease", indications]
      };
    } else {
      // Target-only or no data - don't fetch anything
      return {
        endpoint: "",
        payload: {},
        queryKey: ["DiseasePathways-Empty"]
      };
    }
  };

  const { endpoint, payload, queryKey } = getQueryConfig();
  
  // Should fetch for target+disease combination OR disease-only queries
  const shouldFetch = (target && target.trim().length > 0 && indications && indications.length > 0) || 
                     (!target && indications && indications.length > 0);

  const {
    data: networkBiologyData,
    error: networkBiologyError,
    isLoading: networkBiologyLoading,
  } = useQuery<NetworkBiologyData>(
    queryKey,
    () => fetchData(payload, endpoint),
    { 
      enabled: shouldFetch && endpoint.length > 0,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  // Collapse Panel Styling
  const panelStyle: React.CSSProperties = {
    marginBottom: 5,
    background: "rgb(235 235 235)",
    borderRadius: token.borderRadiusLG,
    border: "none",
    fontFamily: "Poppins",
    padding: "0.3rem 0",
  };

  // Extract unique gene symbols from networkBiologyData
  useEffect(() => {
    if (networkBiologyData) {
      // Create a Set to automatically handle duplicates, then convert back to array
      const uniqueGenes = new Set<string>();
      
      // Add target gene if it exists
      if (target) {
        uniqueGenes.add(target.toUpperCase());
      }
      
      // Add all gene symbols from results, cleaning them first
      Object.values(networkBiologyData).forEach((condition) =>
        condition.results.forEach((result) => {
          result?.gene_symbols?.forEach((symbol) => {
            if (symbol && symbol.toLowerCase() !== "not mentioned") {
              // Trim whitespace and convert to uppercase to handle cases like " GIPR"
              const cleanSymbol = symbol.trim().toUpperCase();
              if (cleanSymbol) {
                uniqueGenes.add(cleanSymbol);
              }
            }
          });
        })
      );

      // Convert Set to sorted array
      setGeneSet(Array.from(uniqueGenes).sort());
    }
  }, [networkBiologyData, target]);

  // Filter disease data based on selected target
  useEffect(() => {
    if (!networkBiologyData) return;

    const filtered = selectedTarget
      ? Object.entries(networkBiologyData)
          .map(([disease, diseaseData]) => ({
            disease,
            results: diseaseData.results.filter((result) => {
              // If the selected target is the same as the original target prop,
              // and we're using target-literature-images endpoint, show all results
              // since they were already filtered by the backend
              const isOriginalTarget = target && selectedTarget.toUpperCase() === target.toUpperCase();
              const isTargetEndpoint = target; // We have a target prop
              
              if (isOriginalTarget && isTargetEndpoint) {
                return true; // Show all results for the original target query
              }
              
              // Otherwise, filter by gene_symbols as before
              return result.gene_symbols?.some(
                (gene) => gene && gene.toUpperCase() === selectedTarget.toUpperCase()
              );
            }),
          }))
          .filter((disease) => disease.results.length > 0)
      : Object.entries(networkBiologyData).map(([disease, diseaseData]) => ({
          disease,
          results: diseaseData.results,
        }));

    setFilteredData(filtered);
  }, [selectedTarget, networkBiologyData, target]);

  // Handle Target Selection Change
  const handleTargetChange = (target?: string) => {
    setSelectedTarget(target);
  };

  useEffect(() => {
    if (!networkBiologyData) {
      setSummary("");
      return;
    }

    if (selectedTarget) {
      // Summary for the selected target
      const summaryJSX = (
        <>
          <span>{selectedTarget}</span> is present in{" "}
          {filteredData.map(({ disease, results }, index) => (
            <span key={index}>
              <span className="text-sky-600">{results.length}</span> pathway
              figure{results.length > 1 ? "s" : ""} of{" "}
              <span>{capitalizeFirstLetter(disease)}</span>
              {index < filteredData.length - 1 ? ", " : "."}
            </span>
          ))}
        </>
      );
      setSummary(summaryJSX);
    } else {
      // Summary for all diseases
      const summaryJSX = (
        <>
          There are{" "}
          {Object.entries(networkBiologyData).map(
            ([disease, diseaseData], index) => (
              <span key={index}>
                <span className="text-sky-600">
                  {diseaseData.results.length}
                </span>{" "}
                pathway figure{diseaseData.results.length > 1 ? "s" : ""} of{" "}
                <span>{capitalizeFirstLetter(disease)}</span>
                {index < Object.entries(networkBiologyData).length - 1
                  ? ", "
                  : "."}
              </span>
            )
          )}
        </>
      );
      setSummary(summaryJSX);
    }
  }, [selectedTarget, filteredData, networkBiologyData]);

  // Don't render if we have no indications, or if we have target but no indications
  if (!indications || indications.length === 0) {
    return null;
  }

  return (
    <section
      id="knowledge-graph-evidence"
      className="px-[5vw] py-20 bg-gray-50 mt-12"
    >
      <h1 className="text-3xl font-semibold">Disease pathways</h1>
      {target ? (
        <p className="mt-2">
          This section offers insights into pathways relevant to pathophysiology and enables users to search disease-related pathways by {target} and/or other genes across one or multiple diseases and visualize their interconnections.
        </p>
      ) : (
        <p className="mt-2">
          This section offers insights into pathways relevant to pathophysiology of {indications.join(", ")} and enables users to search disease-related pathways by genes across one or multiple diseases and visualize their interconnections.
        </p>
      )}

      {geneSet.length > 0 && (
        <div className="my-3">
          <span className="mt-4">Filter by gene: </span>
          <Select
            style={{ width: 300 }}
            showSearch
            placeholder="Select a gene"
            value={selectedTarget}
            onChange={handleTargetChange}
            allowClear
            options={geneSet
              .map((gene) => ({
                label: gene,
                value: gene,
              }))
              .sort((a, b) => a.label.localeCompare(b.label))}
          />
        </div>
      )}
      
      {summary && filteredData.length > 0 && (
        <div className="my-5">
          <span className="font-bold">Summary: </span>
          <span className="text-lg">{summary}</span>
        </div>
      )}

      <div>
        {networkBiologyLoading ? (
          <div className="flex justify-center items-center">
            <LoadingButton />
          </div>
        ) : networkBiologyError ? (
          <div className="h-[70vh] flex justify-center items-center">
            <Empty description={`${networkBiologyError}`} />
          </div>
        ) : filteredData.length > 0 ? (
          <Collapse
            defaultActiveKey={filteredData.map((_, idx) => String(idx + 1))}
            expandIcon={({ isActive }) => (
              <CaretRightOutlined rotate={isActive ? 90 : 0} />
            )}
            bordered={false}
          >
            {filteredData.map((diseaseData, index) => (
              <Collapse.Panel
                key={String(index + 1)}
                header={capitalizeFirstLetter(diseaseData.disease)}
                style={panelStyle}
              >
                <CarouselComponent networkBiologyData={diseaseData} />
              </Collapse.Panel>
            ))}
          </Collapse>
        ) : (
          <div className="h-[70vh] flex justify-center items-center">
            <Empty description={`No data available${selectedTarget ? ` for ${selectedTarget}` : ''}`} />
          </div>
        )}
      </div>
    </section>
  );
};

export default DiseasePathways;