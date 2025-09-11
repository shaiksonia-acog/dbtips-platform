// import { useState, useEffect, useMemo } from "react";
// import { useQuery } from "react-query";
// import { fetchData } from "../../utils/fetchData";
// import DiseaseFilter from "../../components/diseaseFilter";
// import DataTableWrapper from "../../components/dataTableWrapper";
// import { filterByDiseases } from "../../utils/filterDisease";
// import { convertToArray } from "../../utils/helper";
import { Empty } from "antd";
const PatientAdvocacyGroup = ({ indications }) => {
  // const [selectedDisease, setSelectedDisease] = useState(indications);
  console.log("indications", indications);
  // const selectedColumns = [
  //   "disease",
  //   "name",
  //   "country",
  //   "contact",
  // ];
  // const columnDefs = useMemo(
  //   () => [
  //     {
  //       field: "disease",
  //       headerName: "Disease",
  //     },
  //     {
  //       field: "name",
  //       headerName: "Name",
  //       cellRenderer: (params) => {
  //         return (
  //           <a href={params.data.url} target="_blank">
  //             {params.value}
  //           </a>
  //         );
  //       },
  //     },
  //     { field: "country", headerName: "Country" },

  //     { headerName: "Contact", field: "contact" },
  //   ],
  //   []
  // );

  // const payload = {
  //   diseases: indications,
  // };
  // useEffect(() => {
  //   setSelectedDisease(indications);
  // }, [indications]);
  // const { data, error, isLoading } = useQuery(
  //   ["patientAdvocacyGroup", payload],
  //   () => fetchData(payload, "/market-intelligence/patient_advocacy_group/"),
  //   {
  //     enabled: !!indications.length,
  //     refetchOnWindowFocus: false,
  //     staleTime: 5 * 60 * 1000,
  //     refetchOnMount: false,
  //   }
  // );
  // const processedData = useMemo(() => {
  //   if (data) {
  //     return convertToArray(data);
  //   }
  //   return [];
  // }, [data]);
  // const filteredData = useMemo(() => {
  //   return filterByDiseases(processedData, selectedDisease, indications);
  // }, [processedData, selectedDisease, indications]);

  return (
    <div className="px-[5vw] py-10" id="patientAdvocacyGroup">
      <h1 className="text-3xl font-semibold my-3">Patient advocacy groups</h1>
      <p className="my-1 font-medium">Profiles of patient advocacy organisations engaged in disease awareness, patient support and healthcare policy advocacy.</p>
      <div className="h-[40vh] flex items-center justify-center">
              <Empty description="Available on demand" />
            </div>
    </div>
  );
};

export default PatientAdvocacyGroup;
