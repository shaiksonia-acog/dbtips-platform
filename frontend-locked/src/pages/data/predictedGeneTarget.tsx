import Table from "../../components/table";
import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import LoadingButton from "../../components/loading";
import { Empty } from "antd";
import { useMemo } from "react";
function convertToArray(data: any) {
  const result: any[] = [];
  Object.keys(data).forEach((disease) => {
    data[disease]?.forEach((record: any) => {
      result.push({
        ...record,
        postion: disease,
      });
    });
  });
  return result;
}
const PredictedGeneTarget = ({ target }) => {
  const payload = {
    target: target,
  };
  
  const {
    data: predictedGeneTargetData,
    error: predictedGeneTargetError,
    isLoading: predictedGeneTargetLoading,
  } = useQuery(
    ["predictedGeneTargetData", payload],
    () => fetchData(payload, "/target-profile/mir-target-predictions"),
    {
      enabled: !!target,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );

  const processedData = useMemo(() => {
    if (!predictedGeneTargetData) {
      return [];
    }
    return convertToArray(predictedGeneTargetData["mirna_target_predictions"]);
  }, [predictedGeneTargetData]);

  return (
    <div className="px-[5vw] py-20 bg-gray-50" id="predicted-gene-targets">
      <h1 className="text-3xl mb-8 font-semibold">Predicted gene targets </h1>
      {predictedGeneTargetLoading && <LoadingButton />}
      {
        predictedGeneTargetError && (
          <div className="flex justify-center py-20">
            <Empty description="No data available" />
          </div>
        )
      }
      {processedData && !predictedGeneTargetLoading && (
        <Table
          rowData={processedData}
          columnDefs={[
            {
              field: "Representative miRNA",
              headerName: "Representative miRNA",
            },
            {
              field: "Representative Target",
              headerName: "Representative Target",
            },
            { field: "Gene name", headerName: "Gene Name" },
            {
              field: "Cumulative weighted context++ score",
              headerName: "Cumulative Weighted Context++ Score",
            },
            { field: "Aggregate PCT", headerName: "Aggregate PCT" },
            {
              field: "Link to sites in UTR",
              headerName: "Link to Sites in UTR",
              cellRenderer: (params: any) => (
                <a
                  href={params.value}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline"
                >
                  View Sites
                </a>
              ),
            },
          ]}
        />
      )}
    </div>
  );
};

export default PredictedGeneTarget;
