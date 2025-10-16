import { useState, useEffect, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import LoadingButton from "../../components/loading";
import { Empty, Select } from "antd";
import countries from "./countries.yaml";
import { capitalizeFirstLetter } from "../../utils/helper";
import ExportButton from "../../components/exportButton";
import ColumnSelector from "../../components/columnFilter";

const { Option } = Select;

function convertToArray(data) {
  const result = [];
  Object.keys(data).forEach((disease) => {
    data[disease]["results"].forEach((record) => {
      result.push({
        ...record,
        Disease: capitalizeFirstLetter(disease), // Add the disease key
      });
    });
  });
  return result;
}
const PatentLink = (params) => {
  if (!params.data.pdf) {
    return `${params.data.title} (${params.data.patent_id.split("/")[1]})`;
  }

  return (
    <a href={params.data.pdf} target="_blank" rel="noopener noreferrer">
      {`${params.data.title} (${params.data.patent_id.split("/")[1]})`}
    </a>
  );
};

const filterParams = {
  comparator: (filterDate, cellValue) => {
    const cellDate = new Date(cellValue);
    const cellDateStr = `${cellDate.getFullYear()}-${String(
      cellDate.getMonth() + 1
    ).padStart(2, "0")}-${String(cellDate.getDate()).padStart(2, "0")}`;
    const filterDateStr = `${filterDate.getFullYear()}-${String(
      filterDate.getMonth() + 1
    ).padStart(2, "0")}-${String(filterDate.getDate()).padStart(2, "0")}`;
    return cellDateStr.localeCompare(filterDateStr);
  },
  dateFormat: "yyyy-MM-dd",
};

const valueFormatter = (params) => {
  if (!params.value) return "";
  const date = new Date(params.value);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const Patent = ({ target, indications, diseaseAreaFilter }) => {
  const [rowData, setRowData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [countryFilter, setCountryFilter] = useState("All");
  const [selectedDisease, setSelectedDisease] = useState(indications);
  const [statusFilter, setStatusFilter] = useState("ACTIVE");
  const [selectedColumns, setSelectedColumns] = useState([
    "Disease",
    "patent_id",
    "assignee",
    "filing_date",
    "grant_date",
  ]);

  const allColumnDefs = useMemo(() => [
    {
      field: "Disease",
      headerName: "Disease area",
      width: 200,
      cellRenderer: (params) =>
        capitalizeFirstLetter(params.value),
    },
    {
      headerName: "Title",
      field: "patent_id",
      valueGetter: (params) => `${params.data.title} (${params.data.patent_id})`,
      cellRenderer: PatentLink,
      flex: 2,
    },
    {
      headerName: "Current assignee",
      field: "assignee",
      flex: 2,
    },
    {
      headerName: "Filing date",
      field: "filing_date",
      width: 200,
      filter: "agDateColumnFilter",
      filterParams,
      valueFormatter,
    },
    {
      headerName: "Grant date",
      field: "grant_date",
      width: 200,
      filterParams,
      valueFormatter,
    },
    {
      headerName: "Expected expiry date",
      field: "expiry_date",
      flex: 1.1,
      filter: "agDateColumnFilter",
      filterParams,
      valueFormatter,
    },
  ], []);

  const availableColumns = useMemo(() => {
    if (indications.length > 0) {
        return allColumnDefs;
    }
    return allColumnDefs.filter(c => c.field !== 'Disease');
  }, [indications.length, allColumnDefs]);

  const visibleColumns = useMemo(() => {
    return availableColumns.filter((col) => selectedColumns.includes(col.field));
  }, [availableColumns, selectedColumns]);

  const handleColumnChange = (columns) => {
    setSelectedColumns(columns);
  };


  const payload = {
    target: target === "TNFRSF4" ? "OX40" : target,
    diseases: indications,
  };

  const {
    data: patentData,
    error: patentError,
    isLoading: patentLoading,
  } = useQuery(
    ["patentDetails", payload],
    () => fetchData(payload, "/evidence/search-patent/"),
    { enabled: !!target  }
  );
useEffect(() => {
    setSelectedDisease(indications);
  }, [indications]);

  useEffect(() => {
    if (indications.length === 0) {
      setSelectedColumns(cols => cols.filter(c => c !== 'Disease'));
    }
  }, [indications.length]);

  useEffect(() => {
    if (patentData) {
      const flattenedData = convertToArray(patentData)
      console.log("flattenedData", flattenedData);
      setRowData(flattenedData);
    }
  }, [patentData]);

  useEffect(() => {
    const filtered = rowData?.filter((item) => {
      const countryMatch = countryFilter === "All" ||
        item.country_status?.[countryFilter] === statusFilter;
        const diseaseMatch =
        selectedDisease.includes("All") ||
        selectedDisease.some((disease) => item.Disease.toLowerCase() === disease.toLowerCase());
        console.log("disease match", diseaseMatch);
        if (indications.length === 0) {
          console.log("indications length is 0");
          return countryMatch;
        }

      return countryMatch && diseaseMatch;
    });
    console.log("filtered", filtered);
    setFilteredData(filtered);
  }, [countryFilter, statusFilter, rowData, selectedDisease, indications.length]);

  const handleCountryChange = (value) => setCountryFilter(value);
  const handleStatusChange = (value) => setStatusFilter(value);
  const handleDiseaseChange = (value: string[]) => {
		if (value.includes('All')) {
		  // If "All" is selected, select all diseases but don't include "All" in display
		  setSelectedDisease(indications);
		} else if (selectedDisease.length === indications.length && value.length < indications.length) {
		  // If coming from "all selected" state and deselecting, just use the new selection
		  setSelectedDisease(value);
		} else {
		  // Normal selection behavior
		  setSelectedDisease(value);
		}
	  };
  return (
    <section id="patent" className="px-[5vw] py-20 bg-gray-50 mt-12">
      <h1 className="text-3xl font-semibold">Patents</h1>
      <p className=" font-medium mt-2">
        A concise overview of worldwide patents detailing therapeutic
        innovations related to the {target} {indications.length > 0 ? `in ${indications.join(", ")}.`:" in different diseases."}
      </p>

      {patentLoading && <LoadingButton />}
      {patentError && (
        <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[280px] flex items-center justify-center">
          <Empty description={String(patentError)} />
        </div>
      )}
      {!patentLoading && !patentError && filteredData && (
        <div>
         { patentData &&
          <div className="flex justify-between my-3">
            <div className="flex gap-3 flex-wrap   ">
              { indications.length>0 && <div className="flex gap-2">
                <h3 className="mt-1">{diseaseAreaFilter?"Disease Area:":"Disease:"} </h3>
                <Select
                  showSearch
                  placeholder="Select a disease"
                  optionFilterProp="children"
                  mode="multiple"
                  maxTagCount="responsive"
                  onChange={handleDiseaseChange}
                  style={{ width: 250 }}
                  value={selectedDisease}
                >
                  <Option key="All" value="All">
                    All
                  </Option>
                  {indications.map((indication) => (
                    <Option key={indication} value={indication}>
                      {indication}
                    </Option>
                  ))}
                </Select>
              </div>}
              <div className="flex gap-2">
                <h3 className="mt-1">Patent Office: </h3>
                <Select
                  showSearch
                  placeholder="Select a country"
                  optionFilterProp="children"
                  onChange={handleCountryChange}
                  style={{ width: 300 }}
                  value={countryFilter}
                >
                  <Option key="All" value="All">
                    All
                  </Option>
                  {countries.countries.map((country) => (
                    <Option key={country.code} value={country.code}>
                      {`${country.name} (${country.code})`}
                    </Option>
                  ))}
                </Select>
              </div>
              <div className="flex gap-2">
                <h3 className="mt-1">Status: </h3>
                <Select
                  showSearch
                  placeholder="Select a status"
                  optionFilterProp="children"
                  onChange={handleStatusChange}
                  style={{ width: 150 }}
                  value={statusFilter}
                  disabled={countryFilter === "All"}
                >
                  <Option key="Active" value="ACTIVE">
                    Active
                  </Option>
                  <Option key="Inactive" value="NOT_ACTIVE">
                    Inactive
                  </Option>
                  <Option key="Unknown" value="UNKNOWN">
                    Unknown
                  </Option>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              {filteredData.length > 0 && (
                <ColumnSelector
                  allColumns={availableColumns}
                  defaultSelectedColumns={selectedColumns}
                  onChange={handleColumnChange}
                />
              )}
              <ExportButton
                target={target}
                endpoint={"/evidence/search-patent/"}
                fileName="patent"
                indications={indications}
                disabled={patentLoading || filteredData.length === 0}
              />
            </div>
          </div>}
          {filteredData.length === 0 ? (
            <Empty
              className="h-[50vh] flex justify-center items-center flex-col "
              description="No data available  "
            />
          ) : (
            <div>

            
            <div className="ag-theme-quartz mt-4 h-[80vh] max-h-[540px]">
              <AgGridReact
                defaultColDef={{
                  flex: 1,
                  filter: true,
                  sortable: true,
                  floatingFilter: true,
                  headerClass: "font-semibold",
                  autoHeight: true,
                  wrapText: true,
                  cellStyle: { whiteSpace: "normal", lineHeight: "20px" },
                }}
                columnDefs={visibleColumns}
                rowData={filteredData}
                pagination
                paginationPageSize={20}
                enableRangeSelection={true}
                enableCellTextSelection={true}
              />
            </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default Patent;