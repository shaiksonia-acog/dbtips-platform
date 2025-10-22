import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
import { useEffect, useState } from "react";
import ModelStudies from "./model-studies";

const Model = () => {
    const location = useLocation();
    const [indications, setIndications] = useState([]);
    const [diseaseArea, setDiseaseArea] = useState([]);
    
    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const { indications, diseaseArea } = parseQueryParams(queryParams);
        setIndications(indications);
        setDiseaseArea(diseaseArea);
    }, [location]);
    
    return (
        <ModelStudies 
            indications={indications.length > 0 ? indications : diseaseArea} 
            diseaseAreaFilter={diseaseArea.length > 0 }
        />
    )
}

export default Model