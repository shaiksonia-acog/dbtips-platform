// import { AgGridReact } from "ag-grid-react";
import parse from "html-react-parser";
import { Empty } from "antd";
import Table from "../../components/table";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import LoadingButton from "../../components/loading";
import { useMemo, useState } from "react";
import { convertToArray } from "../../utils/helper";
import ColumnSelector from "../../components/columnFilter";
import { filterByDiseases } from "../../utils/filterDisease";
const SelectedLiterature = ({ selectedIndication, indications }) => {
  const [selectedColumns, setSelectedColumns] = useState([
    "Disease",
    "year",
    "title_text",
  ]);
  const columnDefs = useMemo(
    () => [
      {
        field: "Disease",
        headerName: "Disease",
        flex: 3,
      },
      { field: "year", headerName: "Year", flex: 2 },

      {
        field: "title_text",
        headerName: "Title",
        flex: 10,
        cellRenderer: (params) => {
          return (
            <a href={params.data.title_url} target="_blank">
              {parse(params.value)}
            </a>
          );
        },
      },
    ],
    []
  );
  const handleColumnChange = (columns) => {
    setSelectedColumns(columns);
  };
  const visibleColumns = useMemo(() => {
    return columnDefs.filter((col) => selectedColumns.includes(col.field));
  }, [columnDefs, selectedColumns]);
  const payload = {
    diseases: indications,
  };
  const {
    data: selectedLiteratureData,
    error: selectedLiteratureError,
    isLoading: selectedLiteratureLoading,
    isFetching: selectedLiteratureFetching,
  } = useQuery(
    ["selectedLiterature", selectedIndication],
    () => fetchData(payload, "/evidence/top-10-literature/"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const processedData = useMemo(() => {
    if (selectedLiteratureData) {
      return convertToArray(selectedLiteratureData);
    }
    return [];
  }, [selectedLiteratureData]);

  const rowData = useMemo(() => {
    return filterByDiseases(processedData, selectedIndication, indications);
  }, [processedData, selectedIndication, indications]);
  const showLoading = selectedLiteratureFetching || selectedLiteratureLoading;
  return (
    <div>
      <div className="flex justify-between">
        <h2 className="subHeading text-xl font-semibold ">Select reviews</h2>
        <ColumnSelector
          allColumns={columnDefs}
          defaultSelectedColumns={selectedColumns}
          onChange={handleColumnChange}
        />
      </div>

      {showLoading && <LoadingButton />}
      {selectedLiteratureError && !selectedLiteratureData && (
        <Empty description={String(selectedLiteratureError)} />
      )}
      {selectedLiteratureData && !showLoading && !selectedLiteratureError && (
        <div className=" mt-4  ">
          <Table columnDefs={visibleColumns} rowData={rowData} />
        </div>
      )}
    </div>
  );
};

export default SelectedLiterature;
