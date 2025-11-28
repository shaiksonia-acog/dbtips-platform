import LoadingButton from "../../components/loading";
const highlightSequence = (seq) => {
  return seq?.split("").map((char, index) => {
    const isUpperCase = char === char.toUpperCase() && char.match(/[A-Z]/);
    return (
      <span
        key={index}
        className={isUpperCase ? "text-blue-500" : "text-black"}
      >
        {char}
      </span>
    );
  });
};
const highlightStructure = (str) => {
  const lines = str.split("\n");
  return lines.map((line, lineIndex) => {
    const chars = line.split("").map((char, charIndex) => {
      let color = "text-gray-700";
      if (char.match(/[AUGC]/)) {
        color = "text-blue-600 font-bold";
      }
      return (
        <span key={charIndex} className={color}>
          {char}
        </span>
      );
    });
    return <div key={lineIndex}>{chars}</div>;
  });
};

// Function to highlight structure with colors

const Structure = ({
  data,
  targetDetailsError,
  targetDetailsLoading,
  target,
}) => {
  return (
    <div className=" my-12">
        <div className="px-[5vw] ">
          <h1 className="text-3xl font-semibold" id="sequence">Sequence</h1>
          {targetDetailsLoading && <LoadingButton />}

          {/* Sequence with structure notation */}
          {data && !targetDetailsLoading && !targetDetailsError &&(
            <div className="mb-12 mt-6">
              <div className="bg-gray-50 rounded-xl p-6 border border-gray-200 mb-6">
                <div className="font-mono text-lg leading-relaxed break-all">
                  {highlightSequence(data?.sequence)}
                </div>
                <div className="font-mono text-lg leading-relaxed text-gray-500 mt-2">
                  {data.sequence_msa}
                </div>
              </div>

              {/* 5p and 3p sequences in cards */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-5 border-2 border-blue-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="px-2 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold">
                      {target}-5p
                    </div>
                  </div>
                  <div className="font-mono text-base text-blue-700 font-semibold bg-white rounded-lg p-3">
                    {data["5p"].sequence}
                  </div>
                </div>

                <div className="bg-gradient-to-br from-indigo-50 to-indigo-100 rounded-xl p-5 border-2 border-indigo-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="px-2 bg-indigo-500 rounded-lg flex items-center justify-center text-white font-bold">
                      {target}-3p
                    </div>
                  </div>
                  <div className="font-mono text-base text-indigo-700 font-semibold bg-white rounded-lg p-3">
                    {data["3p"].sequence}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Structure section */}
        <div className="mt-12 px-[5vw] bg-gray-50 py-20">
        <h1 className="text-3xl  font-semibold" id="structure">Structure</h1>
        {targetDetailsLoading && <LoadingButton />}
        {data  && !targetDetailsLoading && !targetDetailsError && (
          <div className="bg-gradient-to-br mt-6 from-blue-50 to-indigo-50 rounded-2xl p-6 overflow-x-auto border border-blue-200">
            <div className="text-lg leading-loose whitespace-pre">
              {highlightStructure(data.structure)}
            </div>
          </div>
        )}
    </div>
    </div>
  );
};

export default Structure;
