import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
import DiseasePathways from "./diseasePathways";
import Literature from "./literature";
import TargetLiterature from "./targetLiterature";


const Evidence = () => {
  const location = useLocation();
  const [indications, setIndications] = useState([]);
  const [diseaseArea, setDiseaseArea] = useState([]);

  const [target, setTarget] = useState("");

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { indications, target ,diseaseArea} = parseQueryParams(queryParams);
    setIndications(indications);
    setDiseaseArea(diseaseArea);
    setTarget(target?.split("(")[0]);
  }, [location]);

  const hasIndications = indications?.length > 0|| diseaseArea?.length > 0;
  const showTargetLiterature = target && (hasIndications || !hasIndications);

  return (
    <div className="evidence-page mt-8">
      {showTargetLiterature ? (
        <TargetLiterature target={target} indications={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0}  />
      ) : (
        <Literature indications={indications} />
      )}
       {hasIndications && <DiseasePathways indications={indications.length > 0 ? indications : diseaseArea} 
         target={target} />}
      
      
    </div>
  );
};

export default Evidence;
