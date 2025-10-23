import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
import { useEffect, useState,  } from "react";
import RnaSeqCard from "./rnaSeqCard";
import AssociatePlot from "./associatePlot";
import PgsCatalog from "./pgsCatalog";
import Variantplot from "./variationPlot"
const Data = () => {
    const location = useLocation();
    const [indications, setIndications] = useState([]);
    const [diseaseArea, setDiseaseArea] = useState([]);
    const [target, setTarget] = useState("");
    useEffect(() => {
        const queryParams = new URLSearchParams(location.search);
        const {  target,indications,diseaseArea } = parseQueryParams(queryParams);
        setIndications(indications);
        setDiseaseArea(diseaseArea);
        setTarget(target);
      }, [location]);
    

  return (
    <div className=" mt-8">
      <div className="px-[5vw]">
      <RnaSeqCard />

      </div>
    
      <div id="GenomicsStudies" className="py-10 px-[5vw] bg-gray-50  ">
        <h1 className="text-3xl font-semibold">Genomics studies</h1>

      <AssociatePlot indications={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0} target={target} />
      <Variantplot diseases={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0}/>
      <PgsCatalog indications={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0}/>
      </div>
      </div>
      
  )
}

export default Data