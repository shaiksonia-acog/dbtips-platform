/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "react-query";
import { Search, RefreshCw, AlertCircle } from "lucide-react";
import LoadingButton from "../../components/loading";
import { fetchData, formatRelativeTime } from "./utils";
import { InProgressWidget } from "./components/InProgressWidget";
import { CompletedWidget } from "./components/CompletedWidget";

export default function Notification() {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [leftPage, setLeftPage] = useState(1);
  const [rightPage, setRightPage] = useState(1);
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null);
  const [relativeTime, setRelativeTime] = useState<string | null>(null);


  const { data, isLoading, isError, error, refetch } = useQuery(
    "progression-tracker-dashboard",
    async () => {  setLastFetchTime(new Date()); return fetchData(); },
    {
      refetchInterval: 1000*60*2,
      refetchOnWindowFocus: false,
      refetchOnMount: false,
      retry: 3,
      staleTime: 5000,
    }
  );
  useEffect(() => {
    if (!lastFetchTime) return;
  
    // function to update label
    const updateRelative = () => {
      setRelativeTime(formatRelativeTime(lastFetchTime));
    };
  
    updateRelative(); // set immediately
    const interval = setInterval(updateRelative, 30000); // update every 30s
  
    return () => clearInterval(interval);
  }, [lastFetchTime]);
  
  const handleRefresh = () => { setLastFetchTime(new Date()); refetch(); };

  const safeData = useMemo(
    () =>
      data || {
        submitted: [],
        processing: [],
        processed: [],
        error: [],
      },
    [data]
  );

  const { combinedData, processedData } = useMemo(() => {
    const { submitted = [], processing = [], processed = [], error = [] } = safeData;

    const combined = [
      ...processing.map((d: any) => ({ ...d, status: "processing" })),
      ...error.map((d: any) => ({ ...d, status: "error" })),
      ...submitted.map((d: any) => ({ ...d, status: "submitted" })),
    ];

    const filterFn = (item: any) =>
      item.disease?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.target?.toLowerCase().includes(searchQuery.toLowerCase());

    return {
      combinedData: combined.filter(filterFn),
      processedData: processed.filter(filterFn),
    };
  }, [searchQuery, safeData]);

  const pageSize = 5;

  if (isLoading) {
    return (
      <main className="bg-gray-50 flex h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <LoadingButton />
      </main>
    );
  }

  if (isError) {
    return (
      <main className="bg-gray-50 flex min-h-screen items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
            <p className="mb-2 text-lg text-red-600">Failed to load dashboard</p>
            <p className="text-sm text-gray-500">
              {error instanceof Error
                ? error.message
                : "An error occurred while fetching data"}
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-4 py-12 pt-8 sm:px-6 lg:px-8">
      {/* Search */}
      <div className="mb-8">
        <div className="relative mx-auto flex max-w-md items-center gap-2">
          <div className="relative flex-grow">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-4">
              <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
            </div>
            <input
              type="text"
              aria-label="Search diseases or targets"
              className="hover:shadow-md block w-full rounded-xl border border-gray-200 bg-white py-3 pl-12 pr-4 text-gray-900 placeholder:text-gray-500 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm transition-all duration-200"
              placeholder="Search diseases or targets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <button
            onClick={handleRefresh}
            className="hover:shadow-md rounded-xl border border-gray-200 bg-white p-3 text-gray-500 shadow-sm transition-all duration-200 hover:text-gray-900 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Refresh data"
          >
            <RefreshCw className="h-5 w-5" />
          </button>
        </div>
        {lastFetchTime && (
  <p className="text-center text-xs text-gray-500 mt-2">
    Last fetch {relativeTime} (
    {lastFetchTime.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })}
    )
  </p>
)}


      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <InProgressWidget
          combinedData={combinedData}
          expandedRow={expandedRow}
          setExpandedRow={setExpandedRow}
          leftPage={leftPage}
          setLeftPage={setLeftPage}
          pageSize={pageSize}
        />
        <CompletedWidget
          processedData={processedData}
          rightPage={rightPage}
          setRightPage={setRightPage}
          pageSize={pageSize}
        />
      </div>
    </main>
  );
}