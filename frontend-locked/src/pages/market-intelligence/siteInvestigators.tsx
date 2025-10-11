import { useState, useEffect, useMemo } from "react";
import { Tooltip } from "antd";
import { PhoneOutlined, MailOutlined } from "@ant-design/icons";
import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import { capitalizeFirstLetter } from "../../utils/helper";
import parse from "html-react-parser";

import DataTableWrapper from "../../components/dataTableWrapper";
import { filterByDiseases } from "../../utils/filterDisease";
import DiseaseFilter from "../../components/diseaseFilter";
const Name = (name, phone, email) => {
  return (
    <div>
      {name}
      {phone && (
        <span>
          <Tooltip title={phone}>
            <PhoneOutlined className="ml-1 " />
          </Tooltip>
        </span>
      )}
      {email && (
        <span>
          <Tooltip title={email}>
            <MailOutlined className="ml-2" />
          </Tooltip>
        </span>
      )}
    </div>
  );
};
const IdLink = ({ value }) => {
  return (
    <a
      href={`https://clinicaltrials.gov/study/${value}`}
      target="_blank"
      rel="noopener noreferrer"
    >
      {value}
    </a>
  );
};
const convertToArray = (data) =>
  Object.entries(data)
    .map(([disease, nctData]) => {
      return Object.entries(nctData)
        .map(([nctId, trials]) => {
          return trials.map((trial) => ({
            Disease: disease,
            nctId,
            name: trial.name,
            affiliation: parse(trial.affiliation),
            location: trial.location,
            contact: trial.contact,
            type: trial.type,
          }));
        })
        .flat();
    })
    .flat();

const SiteInvestigators = ({ indications }) => {
  const [selectedDisease, setSelectedDisease] = useState(indications);
  const selectedColumns = [
    "Disease",
    "location",
    "nctId",
    "name",
    "affiliation",
    "contact",
  ];

  const payload = { diseases: indications };
  const columnDefs = useMemo(
    () => [
      {
        field: "Disease",
        headerName: "Disease",
        cellRenderer: (params) => {
          return capitalizeFirstLetter(params.value);
        },
      },
      {
        headerName: "Location",
        field: "location",
        flex: 1.5,
      },
      {
        headerName: "Trial ID",
        field: "nctId",
        cellRenderer: IdLink,
      },
      {
        headerName: "Principal investigator",
        field: "name",
        cellRenderer: (params) =>
          Name(params.value, params.data.phone, params.data.email),
      },
      {
        headerName: "Affiliation",
        field: "affiliation",
        flex: 1.5,
      },

      {
        headerName: "Site contact",
        field: "contact",
        cellRenderer: (params) =>
          Name(params.value.name, params.value.phone, params.value.email),
      },
    ],
    []
  );

  const {
    data: siteInvestigatorsData,
    error: siteInvestigatorsError,
    isLoading: siteInvestigatorsLoading,
  } = useQuery(
    ["siteInvestigatorsDetails", payload],
    () => fetchData(payload, "/market-intelligence/kol/"),
    {
      enabled: !!indications.length,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      staleTime: 5 * 60 * 1000,
    }
  );
  useEffect(() => {
    setSelectedDisease(indications);
  }, [indications]);
  const processedData = useMemo(() => {
    if (siteInvestigatorsData) {
      return convertToArray(siteInvestigatorsData);
    }
    return [];
  }, [siteInvestigatorsData]);
  const filteredData = useMemo(() => {
    return filterByDiseases(processedData, selectedDisease, indications);
  }, [processedData, selectedDisease, indications]);

  return (
    <div id="siteInvetigators">
      <h2 className="text-xl subHeading font-semibold mb-3 mt-2">
        Site Investigators
      </h2>
      <DataTableWrapper
        isLoading={siteInvestigatorsLoading}
        error={siteInvestigatorsError}
        data={processedData}
        filterData={filteredData}
        allColumns={columnDefs}
        defaultColumns={selectedColumns}
        exportOptions={{
          endpoint: "/market-intelligence/kol/",
          fileName: "siteInvestigators",
          indications,
        }}
        filterComponent={
          <DiseaseFilter
            allDiseases={indications}
            selectedDiseases={selectedDisease}
            onChange={setSelectedDisease}
            disabled={siteInvestigatorsLoading}
            width={500}
          />
        }
      />
    </div>
  );
};

export default SiteInvestigators;
