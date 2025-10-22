// import { useState, useEffect, useMemo } from "react";
// import { useQuery } from "react-query";
// import { fetchData } from "../../utils/fetchData";
// import { capitalizeFirstLetter } from "../../utils/helper";
import SiteInvestigators from "./siteInvestigators";
// import { filterByDiseases } from "../../utils/filterDisease";
import { Empty} from "antd";

// import DiseaseFilter from "../../components/diseaseFilter";
// import DataTableWrapper from "../../components/dataTableWrapper";

// function convertToArray(data) {
//   const result = [];
//   Object.keys(data).forEach((disease) => {
//     data[disease].forEach((record) => {
//       result.push({
//         Disease: disease, // Add the disease key
//         name: record.name,
//         expertise: record.expertise,
//         affiliation: record.affiliation,
//         notable_talks: {
//           text: record?.notable_talks?.text || "",
//           url: record?.notable_talks?.url || "",
//         },
//         publications: {
//           text: record?.publications ? "View Publication" : "",
//           url: record?.publications?.length ? record.publications[0] : "",
//         },
//       });
//     });
//   });
//   return result;
// }

// const TrialIDLink = ({ value }) => {
//   return (
//     <a href={`${value.url}`} target="_blank" rel="noopener noreferrer">
//       {value.text}
//     </a>
//   );
// };

const Kol = ({ indications }) => {
  // const [selectedDisease, setSelectedDisease] = useState(indications);
  console.log("indications", indications);
  // const selectedColumns = [
  //   "Disease",
  //   "name",
  //   "affiliation",
  //   "expertise",
  //   "notable_talks",
  //   "publications",
  // ];
  // const payload = { diseases: indications };

  // const {
  //   data: influencersData,
  //   error: influencerError,
  //   isLoading: influencerLoading,
  // } = useQuery(
  //   ["influencerDetails", payload],
  //   () => fetchData(payload, "/market-intelligence/key-influencers/"),
  //   {
  //     enabled: !!indications.length,
  //     refetchOnWindowFocus: false,
  //     staleTime: 5 * 60 * 1000,
  //     refetchOnMount: false,
  //   }
  // );

  // Effect to automatically select the first disease when data is loaded

  // const columnDefs = useMemo(
  //   () => [
  //     {
  //       field: "Disease",
  //       headerName: "Disease",
  //       cellRenderer: (params) => {
  //         return capitalizeFirstLetter(params.value);
  //       },
  //     },
  //     {
  //       headerName: "Name",
  //       field: "name",
  //       sortable: true,
  //       filter: true,
  //       flex: 1,
  //     },
  //     {
  //       headerName: "Affiliation",
  //       field: "affiliation",
  //       sortable: true,
  //       filter: true,
  //       flex: 1,
  //     },
  //     {
  //       headerName: "Expertise",
  //       field: "expertise",
  //       sortable: true,
  //       filter: true,
  //       flex: 1.5,
  //     },
  //     {
  //       headerName: "Notable talks",
  //       field: "notable_talks",
  //       cellRenderer: TrialIDLink,
  //       flex: 1,
  //     },
  //     {
  //       headerName: "Publications",
  //       field: "publications",
  //       cellRenderer: TrialIDLink,
  //       flex: 1,
  //     },
  //   ],
  //   []
  // );

  // useEffect(() => {
  //   if (indications && indications.length > 0) {
  //     setSelectedDisease([...indications]);
  //   }
  // }, [indications]);

  // const processedData = useMemo(() => {
  //   if (influencersData) {
  //     return convertToArray(influencersData);
  //   }
  //   return [];
  // }, [influencersData]);
  // const rowData = useMemo(() => {
  //   return filterByDiseases(processedData, selectedDisease, indications);
  // }, [processedData, selectedDisease, indications]);

  return (
    <article>
      <h1 className="text-3xl font-semibold mb-3">Opinion leaders</h1>
      <p className="mt-1  font-medium mb-2">
        Opinion leaders are experts driving innovation in disease research,
        bridging basic science and clinical application to advance diagnostics
        and therapies.{" "}
      </p>
      <SiteInvestigators indications={indications} />
      <h2 className="text-xl subHeading font-semibold mb-3 mt-2" id="kol">
        Key influential leaders
      </h2>

      {/* <DataTableWrapper
        isLoading={influencerLoading}
        error={influencerError}
        data={processedData}
        filterData={rowData}
        allColumns={columnDefs}
        defaultColumns={selectedColumns}
        exportOptions={{
          endpoint: "/market-intelligence/key-influencers/",
          indications,
          fileName: "keyInfluentialLeaders",
        }}
        filterComponent={
          <DiseaseFilter
            allDiseases={indications}
            selectedDiseases={selectedDisease}
            onChange={setSelectedDisease}
            disabled={influencerLoading}
            width={500}
          />
        }
      /> */}
        <div className="h-[40vh] flex items-center justify-center">
              <Empty description="Available on request" />
            </div>
    </article>
  );
};

export default Kol;
