import { useState, useMemo, useEffect, useCallback } from "react";
import { Empty, Modal } from "antd";
import LoadingButton from "../../components/loading";
import Table from "../../components/table";
import { capitalizeFirstLetter } from "../../utils/helper";
import ColumnSelector from "../../components/columnFilter";
import { useQuery } from "react-query";
import BlackboxWarningCard from "./blackboxWarningCard";
import { fetchData } from "../../utils/fetchData";
import DiseaseFilter from "../../components/diseaseFilter";
function createApprovedDrugsPayload(data) {
  const diseaseMap = {};
  data.forEach(({ Disease, Drug }) => {
    const cleanedDrugName = Drug?.split("(")[0].trim();
    if (!diseaseMap[Disease]) {
      diseaseMap[Disease] = new Set();
    }
    diseaseMap[Disease].add(cleanedDrugName);
  });
  return Object.entries(diseaseMap).map(([disease, drugsSet]) => ({
    disease,
    approved_drugs: Array.from(drugsSet as Set<string>),
  }));
}
const ApprovedDrug = ({
  approvedDrugData,
  loading,
  error,
  indications,
  isFetchingData,
  target,
  diseaseAreaFilter
}) => {
  console.log("diseaseAreaFilter",diseaseAreaFilter);
  const [selectedDisease, setSelectedDisease] = useState([]);
  const [selectedDiseaseArea, setSelectedDiseaseArea] = useState([]);
  const [openModal, setOpenModal] = useState(false);
  const [modalData, setModalData] = useState(undefined);
  const [payload, setPayload] = useState({});
  const [selectedColumns, setSelectedColumns] = useState([
    "diseaseArea",
    "Disease",
    "Target",
    "Drug",
    "blackbox",
  ]);
  console.log("approvedDrugData", approvedDrugData);
  useEffect(() => {
    if(!diseaseAreaFilter)
    setSelectedDisease(indications);
    setSelectedDiseaseArea(diseaseAreaFilter ? [...indications] : []);
  }, [diseaseAreaFilter,indications]);

  const {
    data: blackboxWarningData,
    error: blackboxWarningError,
    isLoading: blackboxWarningIsLoading,
  } = useQuery(
    ["blackboxwarning", payload],
    () => fetchData(payload, "/market-intelligence/blackbox-warnings"),
    {
      enabled: Object.keys(payload).length > 0,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  const handleWarningClick = useCallback((warnings, toxicityClass) => {
    const filtered = Array.isArray(warnings)
      ? warnings.filter(
          (w) =>
            w &&
            typeof w === "object" &&
            "toxicityClass" in w &&
            w.toxicityClass === toxicityClass
        )
      : [];
    setModalData(
      filtered.filter(
        (item) =>
          item &&
          typeof item === "object" &&
          "warningType" in item &&
          "toxicityClass" in item
      )
    );
    setOpenModal(true);
  }, []);
  // Create the blackbox cell renderer as a separate function for clarity
  const renderBlackboxCell = useCallback(
    (params) => {
      if (!blackboxWarningData?.warning) return "No";

      const allDrugs = Object.values(blackboxWarningData.warning).flat();
      const drug = allDrugs.find(
        (item) =>
          item &&
          typeof item === "object" &&
          "drug" in item &&
          item.drug === params.data.Drug
      );

      if (
        drug &&
        typeof drug === "object" &&
        "drugWarnings" in drug &&
        Array.isArray(drug.drugWarnings) &&
        drug.drugWarnings.length > 0
      ) {
        return (
          <div>
            {drug.drugWarnings.map(
              (warning, index) =>
                warning.toxicityClass != null && (
                  <span
                    key={`${warning.toxicityClass}-${index}`}
                    onClick={() =>
                      handleWarningClick(
                        drug.drugWarnings,
                        warning.toxicityClass
                      )
                    }
                  >
                    <span className="underline cursor-pointer">
                      {warning.toxicityClass}
                    </span>

                    {Array.isArray(drug.drugWarnings) &&
                    index < drug.drugWarnings.length - 1
                      ? " | "
                      : ""}
                  </span>
                )
            )}
          </div>
        );
      }
      if (
        drug &&
        typeof drug === "object" &&
        "blackboxWarning" in drug &&
        "chemblAvailable" in drug
      ) {
        if (!drug.blackboxWarning && !drug.chemblAvailable) {
          return "No data available";
        }
      }
      return "No";
    },
    [blackboxWarningData, handleWarningClick]
  );
  const columnDefs = useMemo(
    () => [
      ...(diseaseAreaFilter
        ? [
          {
            field: "diseaseArea",
            headerName: "Disease Area",
            flex: 2,
          },
        ]
        : []),
      {
        field: "Disease",
        cellRenderer: (params) => capitalizeFirstLetter(params.value),
      },
      { field: "Drug" },
      {
        headerName: "Blackbox warning",
        field: "blackbox",
        cellRenderer: renderBlackboxCell,
      },
    ],
    [renderBlackboxCell]
  );
  const visibleColumns = useMemo(
    () => columnDefs.filter((col) => selectedColumns.includes(col.field)),
    [columnDefs, selectedColumns]
  );
  const handleColumnChange = (columns) => {
    setSelectedColumns(columns);
  };
  const areaFilteredData = useMemo(() => {
    if (!approvedDrugData) return [];
    if (selectedDiseaseArea.length === 0) return [];
    return approvedDrugData.filter((data) =>
      selectedDiseaseArea.some(
        (disease) =>
          disease.toLowerCase() === data.diseaseArea?.toLowerCase()
      )
    );
  }, [approvedDrugData, selectedDiseaseArea]);
  const filteredData = useMemo(() => {
    if (!approvedDrugData) return [];
    // const data = areaFilteredData
    // const diseaseAreaFiltered =
    //  filterByDiseases(approvedDrugData, selectedDisease, indications,"diseaseArea");
    // console.log("diseaseAreaFiltered", diseaseAreaFiltered);

    const filtered =
      selectedDisease.length === 0
        ? areaFilteredData?.filter(
            (data) => data.ApprovalStatus === "Approved"
          )
        : areaFilteredData?.filter(
            (data) =>
              selectedDisease.some(
                (disease) =>
                  disease.toLowerCase() === data.
                Disease
                .toLowerCase()
              ) && data.ApprovalStatus === "Approved"
          );
    // Unique data filtering
    const uniqueKeys = new Set(
      filtered?.map((item) => `${item.Disease}-${item.Drug.toLowerCase()}`)
    );

    return Array.from(uniqueKeys).map(
      (key) =>
        filtered.find(
          (item) => `${item.Disease}-${item.Drug.toLowerCase()}` === key
        )!
    );
  }, [approvedDrugData, areaFilteredData, selectedDisease]);
  useEffect(() => {
    if (filteredData.length > 0) {
      const payload = createApprovedDrugsPayload(filteredData);
      setPayload(payload);
    }
  }, [filteredData]);


  const showLoading = isFetchingData || loading || blackboxWarningIsLoading;
  const diseaseOptions = useMemo(() => {
    const diseases = approvedDrugData.map((i) => i.Disease).filter(Boolean);
    return [...new Set(diseases)].sort();
  }, [approvedDrugData]);
  const diseaseAreaOptions = useMemo(() => {
    const diseases = approvedDrugData.map((i) => i.diseaseArea).filter(Boolean);
    return [...new Set(diseases)].sort();
  }, [approvedDrugData]);
  return (
    <section id="approvedDrug" className="px-[5vw]">
      <h1 className="text-3xl font-semibold mb-4">Approved drugs</h1>
      {indications.length > 0 ? (
        <p className="mt-2 font-medium mb-2">
          This section lists drugs targeting {target} that have been approved by
          regulatory authorities for {indications.join(", ")} and/or other
          diseases.
        </p>
      ) : (
        <p className="mt-2 font-medium mb-2">
          This section lists drugs targeting {target} that have been approved by
          regulatory authorities for one or more diseases.
        </p>
      )}
      {diseaseOptions.length > 0 && (
        <div className="flex justify-between">
           <div className="flex gap-4 my-2">
            { diseaseAreaFilter &&  <DiseaseFilter
                      allDiseases={diseaseAreaOptions}
                      selectedDiseases={selectedDiseaseArea}
                      onChange={setSelectedDiseaseArea}
                      labelText="Disease Area:"
                      width={300}
                      placeholder="Select disease area:"
                    />}
              <DiseaseFilter
                      allDiseases={diseaseOptions}
                      selectedDiseases={selectedDisease}
                      onChange={setSelectedDisease}
                      labelText="Disease:"
                      width={300}
                      placeholder="Select diseases"
                      showAllOption={false}
                    />
                     
                    </div>
          <ColumnSelector
            allColumns={columnDefs}
            defaultSelectedColumns={selectedColumns}
            onChange={handleColumnChange}
          />
        </div>
      )}
      {blackboxWarningError && !showLoading && (
        <div className="ag-theme-quartz mt-4 h-[50vh] max-h-[280px] flex items-center justify-center">
          <Empty description={`${blackboxWarningError}`} />
        </div>
      )}
      {showLoading && <LoadingButton />}
      {error && !showLoading && (
        <div className=" mt-4 h-[50vh] max-h-[280px] flex items-center justify-center">
          <Empty description={String(error)} />
        </div>
      )}
      {!showLoading && !error && filteredData && (
        <div className=" mt-1 mb-10">
          <Table
            columnDefs={visibleColumns}
            rowData={filteredData}
            key={blackboxWarningData ? "with-data" : "no-data"} // Force table re-render when data changes
          />
        </div>
      )}
      <Modal
        title="Drug Warnings"
        open={openModal}
        onCancel={() => setOpenModal(false)}
        footer={null}
        width={450}
      >
        {modalData && modalData[0] && (
          <BlackboxWarningCard modalData={modalData} />
        )}
      </Modal>
    
    </section>
  );
};

export default ApprovedDrug;
