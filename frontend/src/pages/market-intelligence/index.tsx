import { useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { parseQueryParams } from "../../utils/parseUrlParams";
import KOL from "./kol";
import PatientStories from "./patientStories";
import PatientAdvocacyGroup from "./patientAdvocacyGroup";
import IndicationPipeline from "./indicationPipeline";
import TargetPipeline from "./targetPipeline";

const CompetitiveLandscape = () => {
  const location = useLocation();
  // const [target, setTarget] = useState('');
  const [indications, setIndications] = useState([]);
  const [target, setTarget] = useState("");
  // const [rowData, setRowData] = useState([]);

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const { indications, target } = parseQueryParams(queryParams);
    setTarget(target?.split("(")[0]);
    setIndications(indications);
  }, [location.search]);
  const showTargetPipeline = target && (indications?.length > 0 || !indications?.length);

  return (
    <div className="mt-8">
      { showTargetPipeline ? (
        <TargetPipeline target={target} indications={indications} />
      ) : (
        <IndicationPipeline indications={indications} />
      )}
      {
        !showTargetPipeline && <div><section
        id="opinionLeaders"
        className="mt-12 min-h-[80vh] mb-10  bg-gray-50 py-20 px-[5vw]"
      >
        <KOL indications={indications} />
      </section>
      <PatientStories indications={indications} />
      <PatientAdvocacyGroup indications={indications} /></div>

      }
      
    </div>
  );
};

export default CompetitiveLandscape;
