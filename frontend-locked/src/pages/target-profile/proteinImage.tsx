import { useEffect, useState } from 'react';
import LoadingButton from '../../components/loading';
import { fetchData } from '../../utils/fetchData';
import { useQuery } from 'react-query';
import { Empty } from 'antd';
import { useLocation } from 'react-router-dom';
import { parseQueryParams } from '../../utils/parseUrlParams';

// Declare the custom element in JSX.IntrinsicElements
declare global {
  namespace JSX {
    interface IntrinsicElements {
      'nightingale-structure': any;
    }
  }
}

import "@nightingale-elements/nightingale-structure";

function ProteinData({  uniprot}) {
  // const uniprot="P43489"
  const [pdbId, setPdbId] = useState(`AF-${uniprot}-F1`);
  const location = useLocation();
	const [target, setTarget] = useState('');
  useEffect(() => {
		const queryParams = new URLSearchParams(location.search);
		const { target } = parseQueryParams(queryParams);
		setTarget(target);
	}, [location]);
  const payload = {
    target: target.split('(')[0]
  };

  const {  error, isLoading } = useQuery(
    ['proteinImage', payload],
    () => fetchData(payload, '/target-profile/protein-structure/'),
    {
      enabled: !!target,
      refetchOnWindowFocus: false,
			staleTime: 5 * 60 * 1000,
			refetchOnMount: false,
      onSuccess: (data) => {
        const pdbReference = data?.dbReferences.find(ref => ref.type === "PDB");
        if (pdbReference) {
          setPdbId(pdbReference.id);
        }
      }
    }
  );
// console.log(data)
  return (
    <div>
      {error && (
        <div className='h-[200px]'>
          <Empty />
        </div>
      )}
      {isLoading ? (
        <LoadingButton />
      ) : (
        <div>
          {
          <nightingale-structure protein-accession={uniprot} structure-id={pdbId} />
        }
        </div>
      )}
    </div>
  );
}

export default ProteinData;
