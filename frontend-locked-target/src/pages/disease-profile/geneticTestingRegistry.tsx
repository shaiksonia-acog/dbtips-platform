import { useQuery } from "react-query";
import { useState, useMemo, useEffect } from "react";
import { fetchData } from "../../utils/fetchData";
import { Modal, Empty } from "antd";
import { convertDiseaseObjectToArray } from "../../utils/helper";
import { filterByDiseases } from "../../utils/filterDisease";
import LoadingButton from "../../components/loading";
import ExportButton from "../../components/exportButton";
import ColumnSelector from "../../components/columnFilter";

import { Select } from "antd";
const { Option } = Select;
import Table from "../../components/table";
``;
/**
 * GeneticTestingRegistry component with reusable DiseaseFilter
 */
const GeneticTestingRegistry = ({ indications, target }) => {
  const [openModal, setOpenModal] = useState(false);
  const [selectedDisease, setSelectedDisease] = useState([...indications]);
  const [selectedGene, setSelectedGene] = useState("");
  const [uniqueGene, setUniqueGene] = useState([]);
  const [geneData, setGeneData] = useState([]);

  const [selectedColumns, setSelectedColumns] = useState([
    "Disease",
    "testname",
    "location",
    "offerer",
    "analytes.Gene",
    "methods",
    "targetpopulation",
  ]);
  const handleDiseaseChange = (value: string[]) => {
    if (value.includes("All")) {
      // If "All" is selected, select all diseases but don't include "All" in display
      setSelectedDisease(indications);
    } else if (
      selectedDisease.length === indications.length &&
      value.length < indications.length
    ) {
      // If coming from "all selected" state and deselecting, just use the new selection
      setSelectedDisease(value);
    } else {
      // Normal selection behavior
      setSelectedDisease(value);
    }
  };

  // Update selectedDisease whenever indications change
  useEffect(() => {
    if (indications && indications.length > 0) {
      setSelectedDisease([...indications]);
    }
  }, [indications]);
  useEffect(() => {
    if (target && typeof target === "string") {
      setSelectedGene(target.toUpperCase());
    }
  }, [target]);

  // Column definitions
  const columnDefs = useMemo(
    () => [
      { field: "Disease", headerName: "Disease" },
      { headerName: "Test Name", field: "testname" },
      { headerName: "Location", field: "location" },
      { field: "offerer", headerName: "Offerer" },
      {
        headerName: "Genes, analytes, and microbes",
        field: "analytes.Gene",
        valueFormatter: (params) => (params.value ? params.value.length : ""),
        cellRenderer: (params) => {
          if (!params.value?.length) return null;

          return (
            <div
              onClick={() => {
                setGeneData(params.value);
                setOpenModal(true);
              }}
              className="underline cursor-pointer"
            >
              {params.value.length}
            </div>
          );
        },
      },
      {
        headerName: "Methods",
        field: "methods",
        valueFormatter: (params) =>
          params.value ? params.value.join(", ") : "",
      },
      { headerName: "Target Population", field: "targetpopulation" },
    ],
    []
  );

  const visibleColumns = useMemo(() => {
    return columnDefs.filter((col) => selectedColumns.includes(col.field));
  }, [columnDefs, selectedColumns]);
  const handleColumnChange = (columns: string[]) => {
    setSelectedColumns(columns);
  };
  // Fetch genetic testing data
  const {
    data: geneticTestingData,
    error: geneticTestingError,
    isLoading: geneticTestingIsLoading,
  } = useQuery(
    ["geneticTesting", { diseases: indications }],
    () =>
      fetchData(
        { diseases: indications },
        "/disease-profile/genetic_testing_registery/"
      ),
    {
      enabled: true,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  // Process the raw data into a flat array
  const processedData = useMemo(
    () =>
      geneticTestingData
        ? convertDiseaseObjectToArray(geneticTestingData, "data")
        : [],

    [geneticTestingData]
  );
  useEffect(() => {
    if (processedData.length > 0) {
      const uniqueGenes = new Set();
      processedData?.forEach((item) => {
        item?.analytes?.Gene?.forEach((gene) => {
          const cleanGene = gene?.split(" ")[0];
          uniqueGenes.add(cleanGene);
        });
      });
      setUniqueGene([...uniqueGenes]);
    }
  }, [processedData]);
  // Filter data when processed data or selected indication changes
  const filteredData = useMemo(() => {
    const filterDisease = filterByDiseases(
      processedData,
      selectedDisease,
      indications
    );

    const filterGene = filterDisease.filter((item) =>
      selectedGene
        ? item?.analytes?.Gene?.some((gene) => {
            const geneName = gene?.split(" ")[0];
            // Ensure `geneName` is a string before calling `toLowerCase`
            return geneName === selectedGene;
          })
        : true
    );

    return filterGene;
  }, [processedData, selectedDisease, indications, selectedGene]);

  return (
    <div id="GTR">
      <div>
        <h2 className="text-xl subHeading font-semibold mb-3">
          Genetic Testing Registry
        </h2>
        <p className="my-1 font-medium">
          List of commercially available genetic testing panels used for
          clinical purposes (diagnosis, predictive, prognosis, risk assessment,
          screening, drug response, etc.) as submitted by the provider.
        </p>
      </div>

      {geneticTestingIsLoading && <LoadingButton />}
      {geneticTestingError && (
        <div className=" h-[50vh] max-h-[280px] flex items-center justify-center">
          <Empty description={` ${geneticTestingError}`} />
        </div>
      )}

      {geneticTestingData && (
        <div>
          <div className="my-4 flex justify-between">
            <div className="flex items-center gap-2">
              <div>
                <span className="mt-4 mr-1">Disease: </span>
                <Select
                  style={{ width: 400 }}
                  onChange={handleDiseaseChange}
                  mode="multiple"
                  value={selectedDisease}
                  disabled={geneticTestingIsLoading}
                  showSearch={false}
                  placeholder="Select indications"
                  maxTagCount="responsive"
                  defaultActiveFirstOption={true}
                >
                  <Option value="All">All</Option>
                  {indications.map((indication) => (
                    <Option key={indication} value={indication}>
                      {indication}
                    </Option>
                  ))}
                </Select>
              </div>
              {uniqueGene.length > 0 && (
                <div >
                  <span className="mt-4 mr-1">Filter by gene:</span>
                  <Select
                    allowClear
                    showSearch
                    style={{ width: 150 }}
                    placeholder="Filter by Gene"
                    onChange={(value) => setSelectedGene(value)}
                    value={selectedGene}
                    className="ml-2"
                    optionFilterProp="children"
                  >
                    {[...uniqueGene]
                      .sort((a, b) => a.localeCompare(b)) // alphabetical sorting
                      .map((gene, index) => (
                        <Option key={index} value={gene}>
                          {gene}
                        </Option>
                      ))}
                  </Select>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <ColumnSelector
                allColumns={columnDefs}
                defaultSelectedColumns={selectedColumns}
                onChange={handleColumnChange}
              />
              <ExportButton
                indications={indications}
                endpoint="/disease-profile/genetic_testing_registery/"
                fileName="GeneticTestingRegistry"
                disabled={processedData.length === 0 || geneticTestingIsLoading}
              />
            </div>
          </div>
          <Table columnDefs={visibleColumns} rowData={filteredData} />
        </div>
      )}

      <Modal
        title="Gene"
        open={openModal}
        onCancel={() => setOpenModal(false)}
        footer={null}
        width={1000}
      >
        <div className="grid grid-cols-4 gap-4 overflow-auto max-h-[400px] p-2">
          {geneData
            .slice()
            .sort((a, b) => a.localeCompare(b))
            .map((gene, index) => (
              <div key={index} className="border-b border-gray-300 pb-1">
                {gene}
              </div>
            ))}
        </div>
      </Modal>
    </div>
  );
};

export default GeneticTestingRegistry;
