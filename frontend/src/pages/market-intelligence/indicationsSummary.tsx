import React, { useMemo, useState } from "react";
import Table from "../../components/table";
import { ConfigProvider, Segmented } from "antd";
import LoadingButton from "../../components/loading";

type TrialData = {
  Target: string;
  OutcomeStatus: "Success" | "Failed" | "Indeterminate" | "Not Known";
  Disease: string;
  ApprovalStatus: string;
  Drug: string;
};

type SummaryFieldMap = {
  approved: string;
  success: string;
  failed: string;
  indeterminate: string;
  notKnown: string;
};

type SummaryData = {
  Target: string;
  [key: string]: string | number;
};

const generateTargetSummary = (
  data: TrialData[],
  keyField: "Disease" | "Drug",
  summaryFieldMap: SummaryFieldMap
): SummaryData[] => {
  const summaryMap: Record<string, SummaryData> = {};
  const statusMaps: Record<keyof SummaryFieldMap, Record<string, Set<string>>> = {
    approved: {},
    success: {},
    failed: {},
    indeterminate: {},
    notKnown: {},
  };

  data.forEach((trial) => {
    const targetList = trial.Target.split(",").map(t => t.trim());
    const keyValue = trial[keyField]; // Disease or Drug

    targetList.forEach((Target) => {
      if (!summaryMap[Target]) {
        summaryMap[Target] = {
          Target,
          [summaryFieldMap.approved]: 0,
          [summaryFieldMap.success]: 0,
          [summaryFieldMap.failed]: 0,
          [summaryFieldMap.indeterminate]: 0,
          [summaryFieldMap.notKnown]: 0,
        };

        for (const key in statusMaps) {
          statusMaps[key as keyof SummaryFieldMap][Target] = new Set<string>();
        }
      }

      if (trial.ApprovalStatus === "Approved") {
        statusMaps.approved[Target].add(keyValue);
      }

      if (trial.OutcomeStatus === "Success") {
        statusMaps.success[Target].add(keyValue);
      } else if (trial.OutcomeStatus === "Failed") {
        statusMaps.failed[Target].add(keyValue);
      } else if (trial.OutcomeStatus === "Indeterminate") {
        statusMaps.indeterminate[Target].add(keyValue);
      } else if (trial.OutcomeStatus === "Not Known") {
        statusMaps.notKnown[Target].add(keyValue);
      }
    });
  });

  Object.keys(summaryMap).forEach((target) => {
    for (const key in summaryFieldMap) {
      const field = summaryFieldMap[key as keyof SummaryFieldMap];
      summaryMap[target][field] = statusMaps[key as keyof SummaryFieldMap][target].size;
    }
  });

  return Object.values(summaryMap);
};


type IndicationsSummaryProps = {
  indicationData: TrialData[];
};

const IndicationsSummary: React.FC<IndicationsSummaryProps> = ({ indicationData }) => {
  const diseaseSummaryData = useMemo(() =>
    generateTargetSummary(indicationData, "Disease", {
      approved: "approvedDrugDiseaseCount",
      success: "successfulDiseaseCount",
      failed: "failedTrialsDiseaseCount",
      indeterminate: "indeterminateTrialsDiseaseCount",
      notKnown: "notKnownDiseaseCount",
    }), [indicationData]);

  const drugSummaryData = useMemo(() =>
    generateTargetSummary(indicationData, "Drug", {
      approved: "approvedDrugCount",
      success: "successfulDrugCount",
      failed: "failedTrialsDrugCount",
      indeterminate: "indeterminateTrialsDrugCount",
      notKnown: "notKnownDrugCount",
    }), [indicationData]);

  const [activeTab, setActiveTab] = useState<string>("diseaseSummaryData");
  const [loading, setLoading] = useState<boolean>(false);
  const handleTabChange = (value: string) => {
    setLoading(true);
    setActiveTab(value);
    setTimeout(() => {
      setLoading(false);
    }, 300); // Adjust time as needed
  };

  const columnDefinitions: Record<string, any[]> = {
    diseaseSummaryData: [
      { headerName: "Target", field: "Target" },
      { headerName: "Approved", field: "approvedDrugDiseaseCount", sort: "desc" },
      { headerName: "Successful", field: "successfulDiseaseCount" },
      { headerName: "Failed", field: "failedTrialsDiseaseCount" },
      { headerName: "Indeterminate", field: "indeterminateTrialsDiseaseCount" },
      { headerName: "Not Known", field: "notKnownDiseaseCount" },
    ],
    drugSummaryData: [
      { headerName: "Target", field: "Target" },
      { headerName: "Approved", field: "approvedDrugCount", sort: "desc" },
      { headerName: "Successful", field: "successfulDrugCount" },
      { headerName: "Failed", field: "failedTrialsDrugCount" },
      { headerName: "Indeterminate", field: "indeterminateTrialsDrugCount" },
      { headerName: "Not Known", field: "notKnownDrugCount" },
    ],
  };

  const tableDataMap = {
    diseaseSummaryData,
    drugSummaryData,
  };

  return (
    <div className="mb-10">
      <h2 className="text-xl subHeading font-semibold mb-3 mt-4">
        Summary of Targets by Outcome
      </h2>
      <p className="mt-2 font-medium">
        Summary of targets with the number of indications for which they are approved or in clinical trials.
      </p>
      <p>
        * The failed entries for the targets include trials that were withdrawn or terminated due to unmet endpoints, financial constraints, or other factors. For detailed explanations, please refer to the respective trial ID from the "List of Trials by Target" table.
      </p>

      <ConfigProvider
        theme={{
          components: {
            Segmented: {
              itemSelectedBg: "#1890ff",
              itemSelectedColor: "white",
            },
          },
        }}
      >
        <Segmented
          options={[
            { label: "Drug Summary Data", value: "drugSummaryData" },
            { label: "Disease Summary Data", value: "diseaseSummaryData" },
          ]}
          value={activeTab}
          onChange={handleTabChange}
          className="my-2"
        />
      </ConfigProvider>

      <div className="ag-theme-quartz mt-4">
  {loading ? (
    <LoadingButton />
  ) : (
    <Table
      columnDefs={columnDefinitions[activeTab]}
      rowData={tableDataMap[activeTab]}
    />
  )}
</div>

    </div>
  );
};

export default IndicationsSummary;
