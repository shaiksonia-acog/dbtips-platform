import { useState, useEffect } from "react";
import AboutTarget from "./about-target";
import Ontology from "./ontology";
import ProteinStructure from "./protein-structure";
import SubCellularLocation from "./sub-cellular-location";
import ProteinExpressions from "./protein-expressions";
import { fetchData } from "../../utils/fetchData";
import { useQuery } from "react-query";
import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
// import TargetHeader from "../../components/targetIndication"
const TargetBiology = () => {
  const location = useLocation();
  const [target, setTarget] = useState("");

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { target } = parseQueryParams(queryParams);
    setTarget(target?.split("(")[0]);
  }, [location]);

  const payload = {
    target: target,
  };

  const {
    data: targetDetailsData,
    error: targetDetailsError,
    isLoading: targetDetailsLoading,
    isFetching: targetDetailFetching,
  } = useQuery(
    ["targetDetails", payload],
    () => fetchData(payload, "/target-profile/details/"),
    {
      enabled: !!target,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
      refetchOnMount: false,
    }
  );
  const { data } = useQuery(
    ["proteinImage", payload],
    () => fetchData(payload, "/target-profile/protein-structure/"),
    {
      enabled: !!target,
    }
  );
  const functionComments = data?.comments
    .filter((comment) => comment.type === "FUNCTION") // Filter for type "FUNCTION"
    .map((comment) => comment.text.map((t) => t.value).join(" ")) // Extract and combine values
    .join(" ");
  const showLoading = targetDetailsLoading || targetDetailFetching;
  return (
    <div>
      <AboutTarget
        data={targetDetailsData}
        targetDetailsError={targetDetailsError}
        targetDetailsLoading={showLoading}
        description={functionComments}
      />
      <Ontology
        hgnc_id={targetDetailsData?.target_details?.hgnc_id}
        target={target}
      />
      <ProteinExpressions target={target} />
      {targetDetailsData?.target_details?.uniprot_id && (
        <ProteinStructure
          uniprot_id={targetDetailsData.target_details.uniprot_id}
        />
      )}

      <SubCellularLocation target={target} />
    </div>
  );
};

export default TargetBiology;
