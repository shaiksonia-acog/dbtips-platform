import { useLocation } from "react-router-dom";
import { parseQueryParams } from "../../utils/parseUrlParams";
import { useEffect, useState,  } from "react";
import RnaSeqCard from "./rnaSeqCard";
import AssociatePlot from "./associatePlot";
import PgsCatalog from "./pgsCatalog";
import Variantplot from "./variationPlot"
import GenomicsHeatmap from "./genomicsHeatmap";
import PredictedGeneTarget from "./predictedGeneTarget";
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
    
const hasIndications = indications.length > 0 || diseaseArea.length > 0;
  return (
    <div >
     { hasIndications && <div className="px-[5vw] mt-8" >
      <RnaSeqCard />

      </div>}
    
      <div id="GenomicsStudies" className={`py-10 px-[5vw] ${hasIndications? "bg-gray-50":""}` }>
        <h1 className="text-3xl font-semibold">Genomics studies</h1>

      { hasIndications && <>
      <AssociatePlot indications={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0} target={target} />
      <Variantplot diseases={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0}/>
      <PgsCatalog indications={indications.length > 0 ? indications : diseaseArea} 
        diseaseAreaFilter={diseaseArea.length > 0}/></>}
        <div className="mt-5" id="genomics-heatmap">
        <h2 className="text-xl subHeading font-semibold mb-3">
        Genomic evidence heatmap{" "}
      </h2>
      <p>
      Summary of evidence from GWAS downstream analyses for gene prioritisation. Counts within the heatmap represent the total of individual contributing results for these methods, combining evidence from across different methods.
      </p>
        <GenomicsHeatmap target={target}/>
        </div>
      </div>
      <PredictedGeneTarget target={target}/>
      </div>
      
  )
}

export default Data