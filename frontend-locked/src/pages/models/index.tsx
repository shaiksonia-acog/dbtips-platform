import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
import { useEffect, useState } from "react";
import ModelStudies from "./model-studies";
import TargetPerturbation from "./targetPertubation";
const Model = () => {
    const location = useLocation();
    const [target, setTarget] = useState("");
    const [indications, setIndications] = useState([]);
    const [diseaseArea, setDiseaseArea] = useState([]);
    
    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const { target,indications, diseaseArea } = parseQueryParams(queryParams);
        setTarget(target);
        setIndications(indications);
        setDiseaseArea(diseaseArea);
    }, [location]);
    const hasIndications = indications?.length > 0|| diseaseArea?.length > 0;
    const showTargetLiterature = target && (hasIndications || !hasIndications);
    return (
        <div>

          { hasIndications && <ModelStudies 
                indications={indications.length > 0 ? indications : diseaseArea} 
                diseaseAreaFilter={diseaseArea.length > 0 }
            />}
            
            {showTargetLiterature && 
            <div className={ hasIndications?"bg-gray-50  py-10 ":""}>

                <TargetPerturbation target={target} />
            </div>}
        </div>
        
    )
}

export default Model