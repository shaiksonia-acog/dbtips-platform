const DescriptionCard = ({ data }) => {
  return (
    <section>
      <article>
        <div className="grid md:grid-cols-2 gap-8">
          {/* Disease Description */}
          <div className="flex-1">
            <h2 className="text-2xl subHeading">Description:</h2>
            <p className="text-base mt-1">{data["Disease Description"].data}</p>
            {/* <small className="block text-gray-600">Source: {data["Disease Description"].source}</small> */}
          </div>

          {/* Synonyms */}
          <div>
            <h2 className="text-2xl subHeading mb-1">Synonyms:</h2>
            <div className="flex flex-wrap gap-2">
              {data["Synonyms"].data.map((synonym, index) => (
                <div
                  key={index}
                  className="px-3 py-1 bg-blue-200 rounded-full text-sm text-gray-700 cursor-pointer"
                >
                  {synonym}
                </div>
              ))}
            </div>
            {/* <small className="block text-gray-600">Source: {data["Synonyms"].source}</small> */}
          </div>

          {/* Prevalence */}
          <div className="flex-1">
            <h2 className="text-2xl subHeading">Prevalence:</h2>
            <p className="text-base mt-1">{data["Prevalence"].data}</p>
            {/* <small className="block text-gray-600">Source: {data["Prevalence"].source}</small> */}
          </div>

          {/* Symptoms */}
          <div className="flex-1">
            <h2 className="text-2xl subHeading">Symptoms:</h2>
            <div>
              <ul className=" grid grid-cols-2 gap-6 list-disc pl-5 space-y-1">
                {data["Symptoms"].data.map((symptom, index) => (
                  <li key={index}>{symptom}</li>
                ))}
              </ul>
            </div>
            {/* <small className="block text-gray-600">Source: {data["Symptoms"].source}</small> */}
          </div>

          {/* Types */}
          <div>
            <h2 className="text-2xl subHeading mb-2">Types:</h2>
            <ul className="space-y-4">
              {data["Types"]?.data.map((type, index) => (
                <li key={index} className="p-3  rounded-lg shadow-md">
                  <h3 className="text-base ">{type}</h3>
                </li>
              ))}
            </ul>
            {/* <small className="block text-gray-600">Source: {data["Types"].source}</small> */}
          </div>

          {/* Phases */}
          <div>
            <h2 className="text-2xl subHeading mb-2">Phases:</h2>
            <ul className="space-y-4">
              {data["Phases"]?.data.map((phase, index) => (
                <li key={index} className="p-3  rounded-lg shadow-md">
                  <h3 className="text-base ">{phase}</h3>
                </li>
              ))}
            </ul>
            {/* <small className="block text-gray-600">Source: {data["Phases"].source}</small> */}
          </div>
        </div>
      </article>
    </section>
  );
};

export default DescriptionCard;
