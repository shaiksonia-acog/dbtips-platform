import Table from "../../components/table";
import { useQuery } from "react-query";
import { fetchData } from "../../utils/fetchData";
import LoadingButton from "../../components/loading";
import { Empty } from "antd";
import { useMemo } from "react";
import CustomHeader from "../../components/customHeader";
import ExportButton from "../../components/exportButton";
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
    () => fetchData(payload, "/target-profile/mir-target-predictions/"),
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
      <h1 className="text-3xl mb-4 font-semibold">Predicted gene targets </h1>
      <p className="mb-2">
      This table summarizes the predicted gene targets for {target} based on TargetScan metrics—namely, the cumulative weighted context++ score and PCT <br />
      *Predictions are derived from TargetScan based on models developed by <a href="http://lens.elifesciences.org/05005/index.html" target="_blank" className="underline">Agarwal et al., 2015</a>, <a target="_blank" href="http://www.ncbi.nlm.nih.gov/pubmed/31806698"className="underline">McGeary, Lin, et al., 2019</a> and <a href="http://genome.cshlp.org/content/19/1/92.long" target="_blank" className="underline">PCT, Friedman et al., 2009</a>.
      </p>
      {predictedGeneTargetLoading && <LoadingButton />}
      {
        predictedGeneTargetError && (
          <div className="flex justify-center py-20">
            <Empty description="No data available" />
          </div>
        )
      }
      {processedData && !predictedGeneTargetLoading && (
        <div>
            <div className="flex justify-end mb-4">
        <ExportButton
          fileName={`predictedGeneTarget-${target}`}
          endpoint={"/target-profile/mir-target-predictions/"}
          target={target}
        />
            </div>
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
              headerComponent: CustomHeader,
              headerComponentParams: {
                title:
                  "Sum of weighted context+ scores across all sites on a transcript; more negative values indicate stronger cumulative repression.",
                  displayName:"Cumulative Weighted Context++ Score"
              },
            },
            { field: "Aggregate PCT", headerName: "Aggregate PCT",
                headerComponent: CustomHeader,
                headerComponentParams: {
                  title:
                    "Probability that a site is evolutionarily conserved; ranges 0–1, with higher values indicating stronger evidence of functional conservation",
                    displayName:"Aggregate PCT"
                },
                cellRenderer: (params: any) => 
                 String(params.value)
        
             },
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
        </div>
      )}
    </div>
  );
};

export default PredictedGeneTarget;
