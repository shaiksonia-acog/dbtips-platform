/* eslint-disable @typescript-eslint/no-explicit-any */
import { useMemo, useState } from "react";
import { Pagination } from "antd";
import { useQuery } from "react-query";
import {
  CheckCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Search,
  Clock,
  AlertCircle,
} from "lucide-react";
import { capitalizeFirstLetter } from "../../utils/helper";
import { Link } from "react-router-dom";
import LoadingButton from "../../components/loading";

const fetchData = async () => {
  const response = await fetch(
    `${import.meta.env.VITE_API_URI}/dossier/progression-tracker-dashboard/`
  );
  if (!response.ok) {
    throw new Error("Network response was not ok");
  }
  return response.json();
};

const buildUrlWithIndications = (baseUrl, target, indications) => {
  const searchParams = new URLSearchParams();

  if (target) searchParams.set("target", target);
  if (indications) {
    // If indications is a string, no need to map and join
    const encodedIndications = `"${indications}"`;
    searchParams.set("indications", encodedIndications);
  }

  return `${baseUrl}?${searchParams.toString()}`;
};

function StatusTag({ status }: { status: string }) {
  const statusConfig: Record<
    string,
    { label: string; className: string; icon?: React.ReactNode }
  > = {
    submitted: {
      label: "SUBMITTED",
      className: "bg-blue-50 text-blue-700 border border-blue-200",
      icon: <Clock className="h-3 w-3" />,
    },
    processing: {
      label: "PROCESSING",
      className: "bg-amber-50 text-amber-700 border border-amber-200",
      icon: <Loader2 className="h-3 w-3 animate-spin" />,
    },
    processed: {
      label: "READY",
      className: "bg-green-50 text-green-700 border border-green-200",
      icon: <CheckCircle className="h-3 w-3" />,
    },
    error: {
      label: "ERROR",
      className: "bg-red-50 text-red-700 border border-red-200",
      icon: <AlertCircle className="h-3 w-3" />,
    },
  };

  const config = statusConfig[status] || {
    label: status.toUpperCase(),
    className: "bg-gray-50 text-gray-700 border border-gray-200",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold tracking-wide ${config.className}`}
      aria-label={`Status: ${config.label}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}

const formatTime = (timeString: string) => {
  const date = new Date(timeString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatStartTime = (timeString: string) => {
  const date = new Date(timeString);
  return (
    date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
    ", " +
    date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
  );
};

const calculateDuration = (startTime: string, endTime: string) => {
  const start = new Date(startTime);
  const end = new Date(endTime);
  const diffMins = Math.round((end.getTime() - start.getTime()) / (1000 * 60));
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? "s" : ""}`;
  const hours = Math.floor(diffMins / 60);
  const mins = diffMins % 60;
  return `${hours} hour${hours !== 1 ? "s" : ""}${
    mins > 0 ? ` ${mins} minute${mins !== 1 ? "s" : ""}` : ""
  }`;
};

const renderDiseaseTarget = (disease?: string, target?: string) => {
  if (target && disease) {
    return disease === "no-disease"
      ? capitalizeFirstLetter(target)
      : `${capitalizeFirstLetter(target)} - ${capitalizeFirstLetter(disease)}`;
  }
  return target?.toUpperCase() || capitalizeFirstLetter(disease || "");
};

export default function Notification() {
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [leftPage, setLeftPage] = useState(1);
  const [rightPage, setRightPage] = useState(1);

  // Fixed useQuery with proper error and loading handling
  const { data, isLoading, isError, error } = useQuery(
    "progression-tracker-dashboard", 
    fetchData,
    {
      refetchInterval: 10000,
      refetchOnWindowFocus: true,
      refetchOnMount: true,
      retry: 3,
      staleTime: 5000,
    }
  );

  // Ensure data exists and has the expected structure
  const safeData = useMemo(() => data || {
    submitted: [],
    processing: [],
    processed: [],
    error: [],
  }, [data]);

  const { combinedData, processedData } = useMemo(() => {
    // Safely destructure with fallbacks
    const {
      submitted = [],
      processing = [],
      processed = [],
      error = [],
    } = safeData;

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
  const paginatedLeft = combinedData.slice(
    (leftPage - 1) * pageSize,
    leftPage * pageSize
  );
  const paginatedRight = processedData.slice(
    (rightPage - 1) * pageSize,
    rightPage * pageSize
  );

  // Handle loading and error states AFTER all hooks
  if (isLoading) {
    return (
      <main className="pt-8 px-4 sm:px-6 lg:px-8 py-12 h-screen bg-gray-50">
        <div className="flex items-center justify-center ">
          <LoadingButton />
        </div>
      </main>
    );
  }

  if (isError) {
    return (
      <main className="pt-8 px-4 sm:px-6 lg:px-8 py-12 min-h-screen bg-gray-50">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600 text-lg mb-2">
              Failed to load dashboard
            </p>
            <p className="text-gray-500 text-sm">
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
    <main className="pt-8 px-4 sm:px-6 lg:px-8 py-12 min-h-screen bg-gray-50">
      {/* Search */}
      <div className="mb-8">
        <div className="relative max-w-md mx-auto">
          <div className="pointer-events-none absolute inset-y-0 left-0 pl-4 flex items-center">
            <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
          </div>
          <input
            type="text"
            aria-label="Search diseases or targets"
            className="block w-full pl-12 pr-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-900 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm transition-all duration-200 hover:shadow-md"
            placeholder="Search diseases or targets..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Widget - In Progress */}
        <section
          className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col"
          aria-labelledby="left-statuses-heading"
        >
          <header className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Loader2
                  className={`h-5 w-5 text-blue-600 ${
                    combinedData.length !== 0 ? "animate-spin" : ""
                  }`}
                  aria-hidden="true"
                />
              </div>
              <div>
                <h3
                  id="left-statuses-heading"
                  className="text-lg font-semibold text-gray-900"
                >
                  In Progress
                </h3>
                <p className="text-sm text-gray-600">
                  {combinedData.length} active dossiers
                </p>
              </div>
            </div>
          </header>

          <div className="divide-y divide-gray-100 overflow-y-auto flex-1">
            {paginatedLeft.length > 0 ? (
              paginatedLeft.map((d: any) => {
                const isExpandable =
                  d.status === "processing" || d.status === "error";
                const isExpanded = expandedRow === d.id;

                return (
                  <div
                    key={d.id}
                    className={`px-6 py-5 transition-all duration-200 ${
                      isExpandable
                        ? "hover:bg-gray-50 cursor-pointer"
                        : "hover:bg-gray-25"
                    }`}
                    onClick={() =>
                      isExpandable && setExpandedRow(isExpanded ? null : d.id)
                    }
                    role={isExpandable ? "button" : undefined}
                    aria-expanded={isExpandable ? isExpanded : undefined}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3 flex-1">
                        {isExpandable && (
                          <div className="mt-1">
                            {isExpanded ? (
                              <ChevronDown
                                className="h-4 w-4 text-gray-400 transition-transform duration-200"
                                aria-hidden="true"
                              />
                            ) : (
                              <ChevronRight
                                className="h-4 w-4 text-gray-400 transition-transform duration-200"
                                aria-hidden="true"
                              />
                            )}
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <h4 className="text-base font-semibold text-gray-900 mb-2 leading-tight">
                            {renderDiseaseTarget(d.disease, d.target)}
                          </h4>
                          <div className="flex items-center gap-2 text-sm text-gray-500">
                            <Clock className="h-4 w-4" />
                            <span>
                              Submitted {formatTime(d.submission_time)}
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="ml-4">
                        <StatusTag status={d.status} />
                      </div>
                    </div>

                    {isExpanded && d.endpointStatus && (
                      <div className="mt-4 ml-7 p-4 bg-gray-50 rounded-lg border border-gray-100">
                        <h5 className="text-sm font-medium text-gray-700 mb-3">
                          Endpoint Progress
                        </h5>
                        <div className="flex gap-8 overflow-x-auto pb-2 divide-x divide-gray-300">
                          {/* Group items into columns of 5 */}
                          {Array.from(
                            {
                              length: Math.ceil(
                                Object.entries(d.endpointStatus).length / 5
                              ),
                            },
                            (_, colIndex) => (
                              <div
                                key={colIndex}
                                className={colIndex > 0 ? "pl-8" : ""}
                              >
                                {Object.entries(d.endpointStatus)
                                  .slice(colIndex * 5, (colIndex + 1) * 5)
                                  .map(([endpoint, statusObj]) => (
                                    <div
                                      key={endpoint}
                                      className="flex justify-between items-center gap-4 py-2"
                                    >
                                      <span className="text-sm text-gray-600 font-mono bg-gray-100 px-2 py-1 rounded whitespace-nowrap">
                                        {endpoint}
                                      </span>
                                      <StatusTag
                                        status={
                                          (statusObj as any)?.status ||
                                          "unknown"
                                        }
                                      />
                                    </div>
                                  ))}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="px-6 py-16 text-center">
                <Loader2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg font-medium">
                  No active dossiers
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  All submissions will appear here
                </p>
              </div>
            )}
          </div>

          {paginatedLeft.length > 0 && (
            <footer className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <Pagination
                current={leftPage}
                pageSize={pageSize}
                total={combinedData.length}
                onChange={setLeftPage}
                showSizeChanger={false}
                size="small"
                aria-label="In progress pagination"
                className="flex justify-center"
              />
            </footer>
          )}
        </section>

        {/* Right Widget - Completed */}
        <section
          className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden flex flex-col"
          aria-labelledby="ready-heading"
        >
          <header className="bg-gradient-to-r from-green-50 to-emerald-50 border-b border-gray-200 px-6 py-5">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle
                  className="h-5 w-5 text-green-600"
                  aria-hidden="true"
                />
              </div>
              <div>
                <h3
                  id="ready-heading"
                  className="text-lg font-semibold text-gray-900"
                >
                  Completed
                </h3>
                <p className="text-sm text-gray-600">
                  {processedData.length} ready dossiers
                </p>
              </div>
            </div>
          </header>

          <div className="divide-y divide-gray-100 overflow-y-auto flex-1">
            {paginatedRight.length > 0 ? (
              paginatedRight.map((d: any) => (
                <div
                  key={d.id}
                  className="px-6 py-5 hover:bg-gray-50 transition-colors duration-200 cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <Link
                      to={buildUrlWithIndications("/", d.target, d.disease)}
                      className="flex items-center gap-x-2 hover:text-black "
                    >
                      <h4 className="text-base font-semibold text-gray-900 group-hover:text-blue-600 transition-colors duration-200 leading-tight">
                        {renderDiseaseTarget(d.disease, d.target)}
                      </h4>
                    </Link>
                    <StatusTag status="processed" />
                  </div>

                  <div className="space-y-1 flex justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Clock className="h-4 w-4" />
                      <span>Started {formatStartTime(d.submission_time)}</span>
                    </div>

                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-green-700 font-medium">
                        Completed in{" "}
                        {calculateDuration(d.submission_time, d.processed_time)}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-6 py-16 text-center">
                <CheckCircle className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg font-medium">
                  No completed dossiers
                </p>
                <p className="text-gray-400 text-sm mt-1">
                  Finished analyses will appear here
                </p>
              </div>
            )}
          </div>

          {paginatedRight.length > 0 && (
            <footer className="px-6 py-4 bg-gray-50 border-t border-gray-200">
              <Pagination
                current={rightPage}
                pageSize={pageSize}
                total={processedData.length}
                onChange={setRightPage}
                showSizeChanger={false}
                size="small"
                aria-label="Completed pagination"
                className="flex justify-center"
              />
            </footer>
          )}
        </section>
      </div>
    </main>
  );
}
