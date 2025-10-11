import { useState } from "react";
import { Select, Tooltip } from "antd";
import Plot from "react-plotly.js";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { Empty } from "antd";
import LoadingButton from "../../components/loading";

const ProteinExpressions = ({ target }) => {
  const [selectedOrgan, setSelectedOrgan] = useState("All");
  const payload = {
    target: target,
  };

  const {
    data: targetProteinExpressionData,
    error: targetProteinExpressionError,
    isLoading: targetProteinExpressioLoading,
  } = useQuery(
    ["targetProteinExpression", payload],
    () => fetchData(payload, "/target-profile/protein-expressions/"),
    {
      enabled: !!target,
    }
  );

  // Extract all organs from the data
  const organKeys = targetProteinExpressionData?.protein_expressions?.data?.map(
    (organObj) => Object.keys(organObj)[0]
  );
  // Get data for the selected organ
  const getOrganData = () => {
    if (selectedOrgan === "All") {
      // When 'All' is selected, combine data from all organs
      const allRNAData = [];
      const allProteinData = [];
      organKeys?.forEach((organKey) => {
        let maxZScore = {
          tissue: "",
          value: 0,
          text: "",
        };
        let maxProteinLevel = {
          tissue: "",
          value: 0,
          text: "",
        };

        const organData =
          targetProteinExpressionData?.protein_expressions?.data?.find(
            (organObj) => organObj[organKey]
          )[organKey];
        organData.forEach((tissue) => {
          if (tissue["RNA Z-Score"] >= maxZScore.value) {
            maxZScore = {
              tissue: organKey,
              value: tissue["RNA Z-Score"],
              text: tissue.Tissue,
            };
          }

          if (tissue["Protein Level"] >= maxProteinLevel.value) {
            maxProteinLevel = {
              tissue: organKey,
              value: tissue["Protein Level"],
              text: tissue.Tissue,
            };
          }
        });
        allRNAData.push(maxZScore);
        allProteinData.push(maxProteinLevel);
      });
      return { rnaData: allRNAData, proteinData: allProteinData };
    } else {
      // When a specific organ is selected, get the relevant data
      const organData =
        targetProteinExpressionData?.protein_expressions?.data?.find(
          (organObj) => organObj[selectedOrgan]
        )[selectedOrgan];
      const rnaData = organData.map((tissue) => ({
        tissue: tissue.Tissue,
        value: tissue["RNA Z-Score"],
      }));
      const proteinData = organData.map((tissue) => ({
        tissue: tissue.Tissue,
        value: tissue["Protein Level"],
      }));
      return { rnaData, proteinData };
    }
  };

  const { rnaData, proteinData } = getOrganData();

  const options = organKeys?.map((organKey: string) => ({ value: organKey }));

  return (
    <section
      id="protein-expression"
      className="mt-12 px-[5vw] bg-gray-50 py-20"
    >
      <div className="flex items-center gap-x-2">
        <h1 className="text-3xl font-semibold">RNA/Protein expressions</h1>
        <Tooltip title="A target is considered to be tissue specific if the z-score is greater than 0.674 (or the 75th percentile of a perfect normal distribution).">
          <span className="material-symbols-outlined">info</span>
        </Tooltip>
      </div>

      <p className="mt-2 font-medium">
        This section provides the baseline RNA and protein expression for{" "}
        {target}.
      </p>

      {/* Error State */}
      {targetProteinExpressionError && <Empty />}
      {targetProteinExpressioLoading && <LoadingButton />}
      {!targetProteinExpressioLoading &&
        !targetProteinExpressionError &&
        !targetProteinExpressionData && (
          <div className="h-[40vh] flex justify-center items-center">
            <Empty description="No data available" />
          </div>
        )}
      {targetProteinExpressionData && (
        <>
          <Select
            defaultValue="All"
            style={{ width: 250, marginTop: 30 }}
            options={[{ value: "All" }, ...(options || [])]}
            value={selectedOrgan}
            onChange={(value) => {
              setSelectedOrgan(value);
            }}
          />

          {/* RNA Z-Score and Protein Level Plot */}
          <div className="flex mt-4 h-[100vh] overflow-scroll w-[100vw]">
            <Plot
              className="w-1/2 overflow-scroll"
              data={[
                {
                  y: rnaData.map((d) => d.tissue),
                  x: rnaData.map((d) => d.value),
                  text: rnaData.map((d) => d.text),
                  type: "bar",
                  orientation: "h",
                  name: "RNA Z-Score",
                  marker: { color: "skyblue" },
                },
              ]}
              layout={{
                title: `RNA Z-Score ${
                  selectedOrgan === "All" ? "by Organ" : `in ${selectedOrgan}`
                }`,
                width: 700,
                height: 800,
                yaxis: {
                  automargin: true,
                },
              }}
            />

            <Plot
              className="w-1/2"
              data={[
                {
                  y: proteinData.map((d) => d.tissue),
                  x: proteinData.map((d) => d.value),
                  text: proteinData.map((d) => d.text),
                  type: "bar",
                  name: "Protein Level",
                  orientation: "h",
                  marker: { color: "salmon" },
                },
              ]}
              layout={{
                title: `Protein Levels ${
                  selectedOrgan === "All" ? "by Organ" : `in ${selectedOrgan}`
                }`,
                height: 760,
                width: 600,
                yaxis: {
                  automargin: true,
                },
              }}
            />
          </div>
        </>
      )}
    </section>
  );
};

export default ProteinExpressions;
