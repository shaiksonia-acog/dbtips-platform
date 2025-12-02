import { useEffect, useState, useMemo, useCallback } from "react";
import { useQuery, useQueries } from "react-query";
import {
  Empty,
  Segmented,
  ConfigProvider,
  Select,
} from "antd";

import { fetchData } from "../../utils/fetchData";
import { capitalizeFirstLetter } from "../../utils/helper";
import LoadingButton from "../../components/loading";
import axios from "axios";
import Table from "../../components/table";
const { Option } = Select;
import ExportButton from "../../components/exportButton";
import ColumnSelector from "../../components/columnFilter";
import { filterByDiseases } from "../../utils/filterDisease";
import DiseaseFilter from "../../components/diseaseFilter";
import CustomHeader from "../../components/customHeader";
import React from "react";

const parseTsvData = (tsvText) => {
  const lines = tsvText.trim().split("\n");
  const headers = lines[0].split("\t");

  return lines.slice(1).map((line) => {
    const values = line.split("\t");
    const entry = {};

    headers.forEach((header, index) => {
      entry[header] = values[index];
    });

    return entry;
  });
};

function convertTODiseaseArray(data) {
  const result = [];

  for (const [disease, path] of Object.entries(data)) {
    if (
      typeof path === "string" &&
      path.includes("cached_data_json/disease")
    ) {
      const mondoId =
        typeof path === "string"
          ? path.split("/").pop()?.split(".")[0]
          : undefined;
      result.push({ disease, mondoId });
    }
  }

  return result;
}

function convertToArray(data) {
  const result = [];
  const diseaseWithoutEFOID = [];
  Object.keys(data).forEach((disease) => {
    if (Array.isArray(data[disease])) {
      data[disease].forEach((record) => {
        result.push({
          ...record,
          pubDate: record["Pub. date"] || null,
          DiseaseArea: capitalizeFirstLetter(disease.replace(/_/g, " ")),
          disease: capitalizeFirstLetter(disease.replace(/_/g, " ")),
        });
      });
    } else {
      diseaseWithoutEFOID.push(disease);
    }
  });

  return { result, diseaseWithoutEFOID };
}

const AssociatePlot = ({ indications, diseaseAreaFilter, target,isRNA }) => {
  const [activeTab, setActiveTab] = useState("association");
  const [selectedDiseaseAreas, setSelectedDiseaseAreas] = useState(indications);
  const [columns, setColumns] = useState([]);
  const [defaultSelectedColumns, setDefaultSelectedColumns] = useState([]);
  const [selectedGene, setSelectedGene] = useState<string[]>([]);
  const [selectedAccession, setSelectedAccession] = useState([]);
  const [selectedColumnsGWASStudies, setSelectedColumnsGWASStudies] = useState([
    "DiseaseArea",
    "disease",
    "Association count",
    "First author",
    "Study accession",
    "pubDate",
    "Journal",
    "Title",
    "Reported trait",
    "Trait(s)",
    "Discovery sample ancestry",
    "Replication sample ancestry",
    "Summary statistics",
  ]);

  useEffect(() => {
    setSelectedDiseaseAreas(indications);
    if (target) setSelectedGene([target]);
    if(target ==="MIR33A" ){
      setSelectedGene(prev => [...prev, "SREBF2"]);
    }
    if(target ==="MIR33B" ){
      setSelectedGene(prev => [...prev, "SREBF1"]);
    }
  }, [indications, diseaseAreaFilter, target, isRNA]);

  const [selectedAssociationColumns, setSelectedAssociationColumns] = useState([
    "DiseaseArea",
    "mapped_diseases",
    "Study Accession",
    "Variant and Risk Allele",
    "pvalue",
    "RAF",
    "OR",
    "BETA",
    "CI",
    "Mapped gene(s)",
  ]);

  
  const gwasColumnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
            {
              field: "disease",
              headerName: "Disease Area",
            },
          ]
        : []),
      {
        field: "Association count",
        maxWidth: 120,
        valueGetter: (params) => {
          if (params.data["Association count"] === "Not available") return "0";
          else if (params.data["Association count"]) {
            return params.data["Association count"];
          } else return "0";
        },
        sort: "desc",
      },
      {
        field: "First author",
      },
      {
        field: "Study accession",
        cellRenderer: (params) => {
          return (
            <a
              href={`https://www.ebi.ac.uk/gwas/studies/${params.value}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {params.value}
            </a>
          );
        },
      },
      {
        field: "pubDate",
        filter: "agDateColumnFilter",
        headerName: "Pub. Date ",
        flex: 2,
      },
      {
        field: "Journal",
      },
      {
        field: "Title",
        minWidth: 200,
      },
      {
        field: "Reported trait",
      },
      {
        field: "Trait(s)",
      },
      {
        field: "Discovery sample ancestry",
      },
      {
        field: "Replication sample ancestry",
        flex: 2,
      },
      {
        field: "Summary statistics",
        cellRenderer: (params) => {
          if (params.value !== "NA") {
            return (
              <a href={params.value} target="_blank" rel="noopener noreferrer">
                FTP download
              </a>
            );
          } else return "Not available";
        },
      },
    ],
    [diseaseAreaFilter]
  );

  const associationColumnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
            {
              field: "DiseaseArea",
              headerName: "Disease Area",
            },
          ]
        : []),
      {
        headerName: "Disease",
        minWidth: 300,
        field: "mapped_diseases",
        cellRenderer: (params) => {
          if (!params.value) return "";
          return params.value
            .map((val) => capitalizeFirstLetter(val))
            .join(" | ");
        },
      },
      {
        headerName: "Study Accession",
        field: "Study Accession",
        cellRenderer: (params) => {
          return (
            <a
              href={`https://www.ebi.ac.uk/gwas/studies/${params.value}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {params.value}
            </a>
          );
        },
      },
      {
        headerName: "Variant and Risk Allele",
        field: "Variant and Risk Allele",
      },
      {
        headerName: "Variant annotation",
        headerClass: "ag-header-cell-center",
        field: "Variant annotation",
        children: [
          {
            field: "Consequence",
            headerName: "Functional consequence",
            cellRenderer: (params) => params.value?.replaceAll("_", " "),
          },
          {
            headerName: "VEP Impact",
            field: "IMPACT",
            headerComponent: CustomHeader,
            headerComponentParams: {
              title: "VEP predicted severity of the variant consequence",
              displayName: "VEP Impact",
            },
            maxWidth: 120,
          },
          {
            headerName: "Alphamissense (pathogenicity & score)",
            field: "am_pathogenicity",
            headerComponent: CustomHeader,
            headerComponentParams: {
              title:
                "Predicted pathogenicity of missense variants ( pathogenic (0.565–1), ambiguous (0.34–0.564), and benign (0–0.33). Pathogenic is predicted to be disease causing",
              displayName: "Alphamissense (pathogenicity & score)",
            },
            valueGetter: (params) =>
              `${params.data["am_pathogenicity"]}, ${params.data["am_class"]}`,
            cellRenderer: (params) =>
              !params.value?.includes("-") && !params.value?.includes("NA")
                ? params.value?.replace("_", " ")
                : "",
          },
          {
            headerName: "CADD",
            headerComponent: CustomHeader,
            headerComponentParams: {
              title:
                "relative deleteriousness of a variant, higher values denote greater functional impact (≥20 = top 1% most deleterious variants)",
              displayName: "CADD",
            },
            field: "CADD_phred",
            maxWidth: 90,
          },
          {
            headerName: "Polyphen-2",
            field: "Polyphen2_HDIV_rankscore",
            headerComponent: CustomHeader,
            headerComponentParams: {
              title:
                " ranked deleteriousness of the variant between 0–1 score (higher = more damaging) ",
              displayName: "Polyphen-2",
            },
            maxWidth: 120,
            cellRenderer: (params) =>
              !params.value?.includes("None")
                ? params.value?.replace("_", " ")
                : "",
          },
          {
            headerName: "SIFT",
            maxWidth: 90,
            headerComponent: CustomHeader,
            headerComponentParams: {
              title: (
                <ul>
                  <li>≥ 0.9 – Among most damaging variants (deleterious)</li>
                  <li>0.7–0.9 – Possibly damaging</li>
                  <li>0.5–0.7 – Uncertain inference</li>
                  <li>&lt; 0.5 – Likely tolerated</li>
                </ul>
              ),
              displayName: "SIFT",
            },
            field: "SIFT4G_converted_rankscore",
            filter: "agNumberColumnFilter",
            cellRenderer: (params) =>
              !params.value?.includes("None") &&
              !params.value?.includes("NA") &&
              !params.value?.includes("-")
                ? params.value?.replace("_", " ")
                : "",
          },
        ],
      },
      {
        headerName: "p-value",
        field: "pvalue",
        agGridColumnType: "numericColumn",
        sort: "asc",
        maxWidth: 100,
        filter: "agNumberColumnFilter",
        comparator: (valueA, valueB) => {
          if (!valueA && !valueB) return 0;
          if (!valueA) return 1;
          if (!valueB) return -1;

          const getExponent = (val) => {
            const str = String(val).toUpperCase();
            const match = str.match(/E([+-]?\d+)/);
            if (!match) return 0;
            return parseInt(match[1], 10);
          };

          const getCoefficient = (val) => {
            const str = String(val).toUpperCase();
            const match = str.match(/^([+-]?\d+\.?\d*)/);
            if (!match) return parseFloat(val);
            return parseFloat(match[1]);
          };

          const expA = getExponent(valueA);
          const expB = getExponent(valueB);

          if (expA !== expB) {
            return expA - expB;
          }

          const coefA = getCoefficient(valueA);
          const coefB = getCoefficient(valueB);
          return coefA - coefB;
        },
      },
      {
        headerName: "RAF",
        field: "RAF",
        maxWidth: 100,
        valueGetter: (params) => {
          if (params.data["RAF"] === "-" || params.data["RAF"] === "NR")
            return "";
          else return params.data["RAF"];
        },
      },
      {
        headerName: "OR",
        field: "OR",
        maxWidth: 100,
        valueGetter: (params) => {
          if (params.data["OR"] === "-" || params.data["OR"] === "NA")
            return "";
          else return params.data["OR"];
        },
      },
      {
        field: "BETA",
        maxWidth: 100,
        valueGetter: (params) => {
          if (params.data["BETA"] === "-" || params.data["BETA"] === "NA")
            return "";
          else return params.data["BETA"];
        },
      },
      {
        headerName: "CI",
        field: "CI",
        valueGetter: (params) => {
          if (params.data["CI"] === "-" || params.data["CI"] === "NA")
            return "";
          else return params.data["CI"];
        },
      },
      {
        headerName: "Mapped Gene",
        field: "Mapped gene(s)",
      },
    ],
    [diseaseAreaFilter]
  );

  const visibleColumns = useMemo(() => {
    if (activeTab === "studies") {
      return gwasColumnDefs.filter((col) =>
        selectedColumnsGWASStudies.includes(col.field)
      );
    } else {
      return associationColumnDefs.filter((col) =>
        selectedAssociationColumns.includes(col.field)
      );
    }
  }, [
    gwasColumnDefs,
    associationColumnDefs,
    selectedColumnsGWASStudies,
    selectedAssociationColumns,
    activeTab,
  ]);

  const handleColumnChange = useCallback((columns: string[]) => {
    if (activeTab === "studies") {
      setSelectedColumnsGWASStudies(columns);
    } else {
      setSelectedAssociationColumns(columns);
    }
  }, [activeTab]);

  const payload = useMemo(() => ({
    diseases: indications,
  }), [indications]);

  const [diseaseData, setDiseaseData] = useState([]);

  useEffect(() => {
    if (activeTab === "studies") {
      setColumns(gwasColumnDefs);
      setDefaultSelectedColumns(selectedColumnsGWASStudies);
    } else {
      setColumns(associationColumnDefs);
      setDefaultSelectedColumns(selectedAssociationColumns);
    }
  }, [
    activeTab,
    associationColumnDefs,
    gwasColumnDefs,
    selectedAssociationColumns,
    selectedColumnsGWASStudies,
  ]);

  const {
    data: vepAssociationsData,
    isLoading: vepAssociationsLoading,
  } = useQuery(
    ["vep-associations", payload],
    () => fetchData(payload, "/genomics/gwas-associations-vep"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const [fallbackDiseases, setFallbackDiseases] = useState<string[]>([]);

  const {
    data: fallbackData,
    error,
    isLoading: fallbackDataLoading,
  } = useQuery(
    ["fallback-mondo-data", fallbackDiseases],
    () => fetchData({ diseases: fallbackDiseases }, "/genomics/gwas-associations"),
    {
      enabled: !!fallbackDiseases.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const [locusZoomData, setLocusZoomData] = useState(null);
  const [locusZoomDataLoading, setLocusZoomDataLoading] = useState(true);

  useEffect(() => {
    if (vepAssociationsLoading || fallbackDataLoading) {
      setLocusZoomDataLoading(true);
      return;
    }

    const newFallbackDiseases: string[] = [];
    const tempLocusZoomData: { [key: string]: any } = {};

    indications.forEach((disease) => {
      if (vepAssociationsData) {
        const matchingKey = Object.keys(vepAssociationsData).find(
          (key) => key.toLowerCase() === disease.toLowerCase()
        );
        if (matchingKey && vepAssociationsData[matchingKey] != null) {
          tempLocusZoomData[disease] = vepAssociationsData[matchingKey];
        } else {
          newFallbackDiseases.push(disease);
        }
      } else {
        newFallbackDiseases.push(disease);
      }
    });

    setFallbackDiseases(newFallbackDiseases);

    if (fallbackData) {
      Object.assign(tempLocusZoomData, fallbackData);
    }

    setLocusZoomData(tempLocusZoomData);
    setLocusZoomDataLoading(false);
  }, [vepAssociationsData, fallbackData, indications, vepAssociationsLoading, fallbackDataLoading]);

  useEffect(() => {
    if (locusZoomData) {
      const convertedData = convertTODiseaseArray(locusZoomData);
      setDiseaseData(convertedData);
    }
  }, [locusZoomData]);

  const queryResults = useQueries(
    diseaseData.map((item) => ({
      queryKey: ["mondo-data", item.mondoId],
      queryFn: async () => {
        const response = await axios.get(
          `${import.meta.env.VITE_API_URI}/api/download/${item.mondoId}.tsv`,
          {
            responseType: "text",
          }
        );
        const parsedData = parseTsvData(response.data);
        return parsedData.map((record) => ({
          ...record,
          DiseaseArea: item.disease,
          mapped_diseases: record["Mapped Trait"]
            ? record["Mapped Trait"].split(",")
            : [],
        }));
      },
      enabled: !!diseaseData.length && !!item.mondoId,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }))
  );

  const isQueriesLoading = queryResults.some((result) => result.isLoading);
  const hasErrors = queryResults.some((result) => result.error);

  const combinedData = useMemo(() => {
    if (isQueriesLoading || hasErrors) return [];

    return queryResults.reduce((accumulator, result) => {
      if (result.data) {
        return [...accumulator, ...result.data];
      }
      return accumulator;
    }, []);
  }, [queryResults, isQueriesLoading, hasErrors]);

  const {
    data: gwasStudiesData,
    error: gwasStudiesError,
    isLoading,
  } = useQuery(
    ["gwas-studies", payload],
    () => fetchData(payload, "/genomics/gwas-studies"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const processedData = useMemo(() => {
    if (gwasStudiesData) {
      const { result } = convertToArray(gwasStudiesData);
      return result;
    }
    return [];
  }, [gwasStudiesData]);

  const rowData = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(
        processedData,
        selectedDiseaseAreas,
        indications,
        "DiseaseArea"
      );
    }
    return processedData;
  }, [processedData, selectedDiseaseAreas, indications, diseaseAreaFilter]);

  const associationsRowData = useMemo(() => {
    if (diseaseAreaFilter) {
      return filterByDiseases(
        combinedData,
        selectedDiseaseAreas,
        indications,
        "DiseaseArea"
      );
    }
    return combinedData;
  }, [combinedData, selectedDiseaseAreas, indications, diseaseAreaFilter]);

  const filterAssociationData = useMemo(() => {
    let filteredData = associationsRowData;

    if (selectedGene.length > 0) {
      filteredData = filteredData.filter((row) => {
        const genes = row["Mapped gene(s)"]
          ? row["Mapped gene(s)"].split(/[;,]+/).map((g) => g.trim())
          : [];

        return selectedGene.some((selected) => {
          const trimmedSelected = selected.trim();
          return genes.some((gene) => {
            if (trimmedSelected.includes("-")) {
              return gene === trimmedSelected;
            }
            if (gene === trimmedSelected) return true;
            const parts = gene.split("-").map((p) => p.trim());
            return parts.includes(trimmedSelected);
          });
        });
      });
    }
    return filteredData;
  }, [associationsRowData, selectedGene]);

  useEffect(() => {
    let newAccessions = [];

    if (selectedGene.length > 0) {
      const geneFilteredData = associationsRowData.filter((row) => {
        const genes = row["Mapped gene(s)"]
          ? row["Mapped gene(s)"].split(/[;,-]+/).map((g) => g.trim())
          : [];
        return selectedGene.some((gene) => genes.includes(gene.trim()));
      });

      const accessions = geneFilteredData.map((row) => row["Study Accession"]);
      newAccessions = [...new Set(accessions)];
    }

    setSelectedAccession((prevAccessions) => {
      const sortedPrev = [...prevAccessions].sort();
      const sortedNew = [...newAccessions].sort();

      const isSame =
        sortedPrev.length === sortedNew.length &&
        sortedPrev.every((val, index) => val === sortedNew[index]);

      if (isSame) {
        return prevAccessions;
      } else {
        return newAccessions;
      }
    });
  }, [selectedGene, associationsRowData]);

  const filteredData = useMemo(() => {
    let filtered = rowData;

    if (selectedAccession.length > 0) {
      filtered = filtered.filter((item) =>
        selectedAccession.includes(item["Study accession"])
      );
    } else if (selectedGene.length > 0) {
      filtered = [];
    }

    return filtered;
  }, [rowData, selectedAccession, selectedGene]);

  const geneOptions = useMemo(() => {
    return Array.from(
      new Set([
        ...(target ? [target] : []),
        ...associationsRowData.flatMap(
          (item) => (item["Mapped gene(s)"] || "").split(/[,;]/)
        ),
      ])
    )
      .filter((gene) => gene.trim() !== "")
      .sort();
  }, [associationsRowData, target]);

  const handleGeneChange = useCallback((value) => {
    setSelectedGene(value);
  }, []);

  const handleTabChange = useCallback((value) => {
    setActiveTab(value);
  }, []);

  return (
    <div className="my-5" id="gwas-studies">
      <div className="flex gap-2">
        <h2 className="text-xl subHeading font-semibold mb-3" id="gwasStudies">
          GWAS studies
        </h2>
        
      </div>
      <p>The GWAS section summarizes genomic associations extracted from the GWAS Catalog, noting that not all relevant studies are captured within the database.</p>

      {locusZoomDataLoading && <LoadingButton />}
      {(gwasStudiesError || error) && (
        <div>
          <Empty description={`${gwasStudiesError}`} />
        </div>
      )}
      {!isLoading && !gwasStudiesError && gwasStudiesData && (
        <div className="mt-4">
          <div className="flex mb-3">
            <div className="flex gap-4">
              {diseaseAreaFilter && (
                <DiseaseFilter
                  allDiseases={indications}
                  selectedDiseases={selectedDiseaseAreas}
                  onChange={setSelectedDiseaseAreas}
                  disabled={isLoading}
                  width={300}
                  labelText={diseaseAreaFilter ? "Disease Area:" : "Disease:"}
                />
              )}
              <div>
                <span className="mt-1 mr-1">Gene: </span>

                <Select
                  style={{ width: 300 }}
                  placeholder="Select a Gene"
                  value={selectedGene}
                  onChange={handleGeneChange}
                  allowClear
                  showSearch
                  virtual={true}
                  listHeight={400}
                  mode="multiple"
                  filterOption={(input, option) =>
                    String(option?.children ?? "")
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                >
                  {geneOptions.map((gene) => (
                    <Option key={gene} value={gene}>
                      {gene}
                    </Option>
                  ))}
                </Select>
              </div>
            </div>
          </div>
          <div className="flex justify-between my-3">
            <div>
              <span>Available Data: </span>
              <ConfigProvider
                theme={{
                  components: {
                    Segmented: {
                      itemSelectedBg: "#1890ff",
                      itemSelectedColor: "white",
                    },
                  },
                }}
              >
                <Segmented
                  options={[
                    { label: "Associations", value: "association" },
                    { label: "Studies", value: "studies" },
                  ]}
                  value={activeTab}
                  onChange={handleTabChange}
                />
              </ConfigProvider>
            </div>
            <div className="flex gap-2">
              <ColumnSelector
                allColumns={columns}
                defaultSelectedColumns={defaultSelectedColumns}
                onChange={handleColumnChange}
              />
              <ExportButton
                indications={indications}
                endpoint="/genomics/gwas-studies"
                fileName="GWAS-Studies"
              />
            </div>
          </div>

          {activeTab === "studies" && (
            <div>
              <Table rowData={filteredData} columnDefs={visibleColumns} />
            </div>
          )}

          {activeTab === "association" && (
            <div>
              <Table
                columnDefs={visibleColumns}
                rowData={filterAssociationData}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default React.memo(AssociatePlot);