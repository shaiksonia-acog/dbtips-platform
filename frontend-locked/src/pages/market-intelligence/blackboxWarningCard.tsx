import { ArrowUpRight, AlertTriangle, BookOpen, MapPin } from 'lucide-react';
import { useMemo } from 'react';
const BlackboxWarningCard = ({modalData}) => {
  const groupedRefs = useMemo(() => {
    if (!modalData || !modalData[0] || !modalData[0].references || !Array.isArray(modalData[0].references)) {
      return {};
    }
    
    return modalData[0].references.reduce((acc, ref, index) => {
      const key = ref.source;
      if (!acc[key]) acc[key] = [];
      acc[key].push({ ...ref, index: index + 1 });
      return acc;
    }, {});
  }, [modalData]);
  return (
    <div 
      className="bg-white rounded-lg overflow-hidden shadow-md border border-gray-100 max-w-md transition-all duration-300 hover:shadow-lg"
      
    >
      {/* Header with toxicity class */}
      <div className="relative p-4" style={{ backgroundColor: `#f59e0b15` }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle size={20} style={{ color: "#f59e0b" }} />
            <h3 className="font-semibold text-lg text-gray-800">
              Toxicity class: {modalData[0]?.toxicityClass || "Not Available"}
            </h3>
          </div>
          
          {modalData[0]?.efoIdForWarningClass && (
            <a
              href={`https://www.ebi.ac.uk/ols4/search?q=${modalData[0].efoIdForWarningClass}`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1 rounded-full transition-transform duration-400 ease-in-out transform hover:scale-150"
            >
              <ArrowUpRight size={18} className="text-blue-600" />
            </a>
          )}
        </div>
        
        {/* Animated bar below header */}
        <div className="absolute bottom-0 left-0 h-1 transition-all duration-500 ease-in-out" 
          style={{ 
            backgroundColor: "#f59e0b", 
          }} 
        />
      </div>
      
      {/* Content area */}
      <div className="p-4 space-y-4">
        {/* Info grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-gray-50 p-3 rounded-md">
            <div className="flex items-center space-x-2 mb-1">
              <MapPin size={16} className="text-gray-500" />
              <span className="text-sm font-medium text-gray-600">Country</span>
            </div>
            <p className="text-gray-800 font-medium pl-6">{modalData[0]?.country || "N/A"}</p>
          </div>
          
          <div className="bg-gray-50 p-3 rounded-md">
            <div className="flex items-center space-x-2 mb-1">
              <BookOpen size={16} className="text-gray-500" />
              <span className="text-sm font-medium text-gray-600">EFO ID</span>
            </div>
            <p className="text-gray-800 font-medium pl-6">{modalData[0]?.efoIdForWarningClass?.split(":")[1] || "N/A"}</p>
          </div>
        </div>
        
        {/* References section */}
        <div className="mt-4">
          <h4 className="text-sm uppercase tracking-wider text-gray-500 font-semibold mb-3 flex items-center">
            <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: "#f59e0b" }}></div>
            References
          </h4>
          
          <div className="space-y-4">
            {Object.entries(groupedRefs).map(([source, refs]) => (
              <div key={source} className="bg-gray-50 p-3 rounded-md">
                <div className="font-medium text-gray-700 mb-2">{source}</div>
                <div className="flex flex-wrap gap-2">
                  {(refs as Array<any>).map((ref) => (
                    <a
                      key={ref.id}
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center px-2 py-1 bg-white rounded border border-gray-200 hover:bg-blue-50 hover:border-blue-200 transition-colors duration-200"
                    >
                      <span className="text-blue-600 text-sm">{ref.index}</span>
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default BlackboxWarningCard
