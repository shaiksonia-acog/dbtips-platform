import { useState, useMemo, useEffect, useCallback } from "react";
import { Empty, Modal } from "antd";
import LoadingButton from "../../components/loading";
import Table from "../../components/table";
import { capitalizeFirstLetter } from "../../utils/helper";
import { fetchData } from "../../utils/fetchData";
import ColumnSelector from "../../components/columnFilter";
import { useQuery } from "react-query";
import BlackboxWarningCard from "./blackboxWarningCard";
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
}) => {
  const [selectedDisease, setSelectedDisease] = useState(indications || []);
  const [openModal, setOpenModal] = useState(false);
  const [modalData, setModalData] = useState(undefined);
  const [payload, setPayload] = useState({});
  const [selectedColumns, setSelectedColumns] = useState([
    "Disease",
    "Target",
    "Drug",
    "blackbox",
  ]);

  const {
    data: blackboxWarningData,
    error: blackboxWarningError,
    isLoading: blackboxWarningIsLoading,
  } = useQuery(
    ["blackboxwarning", payload],
    () => fetchData(payload, "/market-intelligence/blackbox-warnings/"),
    {
      enabled: Object.keys(payload).length > 0,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  // Create a callback that will be invoked in cellRenderer
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
            {drug.drugWarnings.map((warning, index) => (
              warning.toxicityClass!=null &&
              <span
                key={`${warning.toxicityClass}-${index}`}
                onClick={() =>
                  handleWarningClick(drug.drugWarnings, warning.toxicityClass)
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
            ))}
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
  // Make sure columnDefs updates when blackboxWarningData or renderBlackboxCell changes
  const columnDefs = useMemo(
    () => [
      {
        field: "Disease",
        cellRenderer: (params) => capitalizeFirstLetter(params.value),
      },
      { field: "Target" },
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
  const filteredData = useMemo(() => {
    if (!approvedDrugData || !Array.isArray(approvedDrugData)) return [];
    const filtered = selectedDisease.includes("All")
      ? approvedDrugData.filter((data) => data.ApprovalStatus === "Approved")
      : approvedDrugData.filter(
          (data) =>
            selectedDisease.some(
              (disease) => disease.toLowerCase() === data.Disease.toLowerCase()
            ) && data.ApprovalStatus === "Approved"
        );
    const uniqueKeys = new Set(
      filtered.map((item) => `${item.Disease}-${item.Drug}`)
    );
    return Array.from(uniqueKeys).map((key) =>
      filtered.find(
        (item) => `${item.Disease}-${item.Drug}` === key
      )
    );
  }, [selectedDisease, approvedDrugData]);
  useEffect(() => {
    if (filteredData.length > 0) {
      const payload = createApprovedDrugsPayload(filteredData);
      setPayload(payload);
    }
  }, [filteredData]);
  useEffect(() => {
    if (indications && Array.isArray(indications)) {
      setSelectedDisease(indications);
    }
  }, [indications]);
 
  const showLoading = isFetchingData || loading || blackboxWarningIsLoading;

  return (
    <section id="approvedDrug" className="px-[5vw]">
      <h1 className="text-3xl font-semibold mb-4">Approved Drugs</h1>
      <p className="mt-2 font-medium mb-2">
        List of approved drugs for {indications.join(", ")}.
      </p>
      <div className="flex justify-between">
        <div>
        <DiseaseFilter
            allDiseases={indications}
            selectedDiseases={selectedDisease}
            onChange={setSelectedDisease}
            disabled={blackboxWarningIsLoading}
          />
          
        </div>
        <ColumnSelector
          allColumns={columnDefs}
          defaultSelectedColumns={selectedColumns}
          onChange={handleColumnChange}
        />
      </div>
      {showLoading && <LoadingButton />}
      {blackboxWarningError && !showLoading && (
        <div className="ag-theme-quartz mt-4 h-[50vh] max-h-[280px] flex items-center justify-center">
          <Empty description={`${blackboxWarningError}`} />
        </div>
      )}
      {error && !showLoading && (
        <div className="ag-theme-quartz mt-4 h-[50vh] max-h-[280px] flex items-center justify-center">
          <Empty description={`${error}`} />
        </div>
      )}
      {!showLoading && !error && filteredData && (
        <div className="mt-4 mb-10">
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
